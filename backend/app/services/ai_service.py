import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import chromadb
from langchain.callbacks.manager import CallbackManager
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from langchain.schema import Document
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.config import settings
from app import telemetry
from app.guards.rag_answer import assess_rag_answer, rag_fallback_message
from app.guards.retrieval_context import (
    assess_retrieval_for_generation,
    documents_from_results,
)
from app.guards.structured_output import (
    parse_json_array_from_llm,
    validate_flashcard_items,
    validate_quiz_items,
)
from app.observability.langchain_timing import (
    LlmUsageCaptureHandler,
    token_usage_from_chat_message,
)
from app.services.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)


def stamp_chunk_metadata(docs: List[Document], user_id: str, document_id: int) -> None:
    for doc in docs:
        meta = dict(doc.metadata) if doc.metadata else {}
        meta["document_id"] = str(document_id)
        meta["user_id"] = str(user_id)
        doc.metadata = meta


def _similarity_search_filtered(
    vector_store: Chroma,
    question: str,
    top_k: int,
    document_ids: Optional[List[int]],
) -> List[Tuple[Document, float]]:
    k_fetch = (
        min(top_k * 5, settings.rag_top_k_max)
        if document_ids
        else top_k
    )
    results = vector_store.similarity_search_with_score(question, k=k_fetch)
    if document_ids:
        allowed = {str(i) for i in document_ids}
        results = [
            (d, s)
            for d, s in results
            if d.metadata.get("document_id") in allowed
        ][:top_k]
    else:
        results = results[:top_k]
    return results


class AIService:
    def __init__(self) -> None:
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=settings.openai_api_key,
            model="text-embedding-ada-002",
        )
        _llm_kw = dict(
            openai_api_key=settings.openai_api_key,
            model=settings.openai_model,
            max_tokens=settings.openai_max_tokens,
            temperature=settings.openai_temperature,
        )
        try:
            self.llm = ChatOpenAI(
                **_llm_kw, request_timeout=settings.openai_request_timeout
            )
        except TypeError:
            self.llm = ChatOpenAI(**_llm_kw)
        self.vector_store: Optional[Chroma] = None
        self._stuff_qa_chain = load_qa_chain(self.llm, chain_type="stuff")

    def process_document(self, file_path: str, file_type: str) -> List[Document]:
        documents = DocumentProcessor.process_file(file_path, file_type)
        telemetry.log_metrics(
            {
                "document_processed": True,
                "file_type": file_type,
                "chunk_count": len(documents),
            }
        )
        return documents

    def create_embeddings(self, documents: List[Document], collection_name: str) -> Chroma:
        try:
            vector_store = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                persist_directory=settings.chroma_persist_directory,
                collection_name=collection_name,
            )
            vector_store.persist()
            telemetry.log_metrics(
                {
                    "embeddings_created": True,
                    "collection_name": collection_name,
                    "document_count": len(documents),
                }
            )
            return vector_store
        except Exception as e:
            logger.error("Error creating embeddings: %s", e)
            raise

    def delete_document_vectors(self, collection_name: str, document_id: int) -> None:
        try:
            client = chromadb.PersistentClient(path=settings.chroma_persist_directory)
            col = client.get_collection(name=collection_name)
            col.delete(where={"document_id": str(document_id)})
        except Exception as e:
            logger.warning("Chroma delete for document_id=%s: %s", document_id, e)

    def answer_question(
        self,
        question: str,
        collection_name: str,
        top_k: int = 5,
        document_ids: Optional[List[int]] = None,
        metrics_out: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            vector_store = Chroma(
                persist_directory=settings.chroma_persist_directory,
                embedding_function=self.embeddings,
                collection_name=collection_name,
            )

            t_r0 = time.perf_counter()
            scored = _similarity_search_filtered(
                vector_store, question, top_k, document_ids
            )
            retrieval_ms = (time.perf_counter() - t_r0) * 1000.0

            r_assess = assess_retrieval_for_generation(
                scored,
                min_non_empty_chunks=settings.rag_guard_min_chunks,
                min_total_chars=settings.rag_guard_min_context_chars,
                max_best_distance=settings.rag_guard_max_best_distance,
            )

            generation_ms = 0.0
            guard_fallback = False
            guard_reason = ""

            if r_assess.is_failure:
                guard_fallback = True
                guard_reason = "retrieval:" + r_assess.reason
                answer_text = rag_fallback_message(r_assess.reason)
                source_documents: List[Document] = []
            else:
                source_documents = documents_from_results(list(scored))
                context_joined = "\n".join(
                    (d.page_content or "") for d in source_documents
                )
                cb_handler = LlmUsageCaptureHandler()
                cb_manager = CallbackManager([cb_handler])
                t_g0 = time.perf_counter()
                chain_out = self._stuff_qa_chain(
                    {"input_documents": source_documents, "question": question},
                    callbacks=cb_manager,
                )
                generation_ms = (time.perf_counter() - t_g0) * 1000.0
                answer_text = chain_out.get("output_text") or ""

                if cb_handler.last_usage and metrics_out is not None:
                    metrics_out["token_usage"] = cb_handler.last_usage

                ans_assess = assess_rag_answer(
                    answer_text,
                    context_text=context_joined,
                    question=question,
                    min_answer_chars=settings.rag_guard_min_answer_chars,
                    min_context_word_overlap=settings.rag_guard_min_context_word_overlap,
                )
                if not ans_assess.ok:
                    logger.warning(
                        "guard_fallback rag_answer post_check reason=%s",
                        ans_assess.reason,
                    )
                    guard_fallback = True
                    guard_reason = "answer:" + ans_assess.reason
                    answer_text = rag_fallback_message(ans_assess.reason)

            source_docs = []
            for doc in source_documents:
                source_docs.append(
                    {
                        "content": doc.page_content[:200] + "...",
                        "metadata": doc.metadata,
                    }
                )

            if metrics_out is not None:
                metrics_out["retrieval_ms"] = round(retrieval_ms, 4)
                metrics_out["generation_ms"] = round(generation_ms, 4)
                metrics_out["retrieved_chunks"] = len(source_documents)
                metrics_out["guard_fallback"] = guard_fallback
                if guard_reason:
                    metrics_out["guard_reason"] = guard_reason

            response: Dict[str, Any] = {
                "answer": answer_text,
                "sources": source_docs,
                "question": question,
            }
            if guard_fallback:
                response["guard_fallback"] = True
                response["guard_reason"] = guard_reason

            telemetry.log_metrics(
                {
                    "question_answered": True,
                    "question_length": len(question),
                    "answer_length": len(answer_text),
                    "source_count": len(source_docs),
                    "filtered_documents": len(document_ids) if document_ids else 0,
                    "rag_guard_fallback": guard_fallback,
                }
            )
            return response
        except Exception as e:
            logger.error("Error answering question: %s", e)
            raise

    def generate_quiz(
        self,
        content: str,
        num_questions: int = 5,
        metrics_out: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        try:
            prompt_template = PromptTemplate(
                input_variables=["content", "num_questions"],
                template="""
                Based on the following content, generate {num_questions} multiple choice questions.
                Each question should have 4 options (A, B, C, D) with only one correct answer.

                Content: {content}

                Format your response as a JSON array with the following structure:
                [
                    {{
                        "question": "Question text here?",
                        "options": ["Option A", "Option B", "Option C", "Option D"],
                        "correct_answer": "A",
                        "explanation": "Explanation of why this is correct"
                    }}
                ]

                Make sure the questions are educational and test understanding of the content.
                """,
            )

            prompt = prompt_template.format(
                content=content, num_questions=num_questions
            )
            response = self.llm.invoke(prompt)
            if metrics_out is not None:
                tu = token_usage_from_chat_message(response)
                if tu:
                    metrics_out["token_usage"] = tu

            raw = response.content
            items, err = parse_json_array_from_llm(raw)
            if err:
                logger.warning("guard_fallback structured_output kind=quiz reason=%s", err)
                raise ValueError(f"Could not parse quiz JSON: {err}")
            ok, reason = validate_quiz_items(items, num_questions)
            if not ok:
                logger.warning(
                    "guard_fallback structured_output kind=quiz reason=%s", reason
                )
                raise ValueError(f"Invalid quiz structure: {reason}")

            quiz_questions = items[:num_questions]

            telemetry.log_metrics(
                {
                    "quiz_generated": True,
                    "question_count": len(quiz_questions),
                    "source_content_length": len(content),
                }
            )
            return quiz_questions

        except Exception as e:
            logger.error("Error generating quiz: %s", e)
            raise

    def generate_flashcards(
        self,
        content: str,
        num_cards: int = 10,
        metrics_out: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        try:
            prompt_template = PromptTemplate(
                input_variables=["content", "num_cards"],
                template="""
                Based on the following content, generate {num_cards} flashcards.
                Each flashcard should have a front (question/concept) and back (answer/explanation).

                Content: {content}

                Format your response as a JSON array with the following structure:
                [
                    {{
                        "front": "Front of the card (question or concept)",
                        "back": "Back of the card (answer or explanation)"
                    }}
                ]

                Make the flashcards concise but informative, covering key concepts from the content.
                """,
            )

            prompt = prompt_template.format(content=content, num_cards=num_cards)
            response = self.llm.invoke(prompt)
            if metrics_out is not None:
                tu = token_usage_from_chat_message(response)
                if tu:
                    metrics_out["token_usage"] = tu

            raw = response.content
            items, err = parse_json_array_from_llm(raw)
            if err:
                logger.warning(
                    "guard_fallback structured_output kind=flashcards reason=%s", err
                )
                raise ValueError(f"Could not parse flashcards JSON: {err}")
            ok, reason = validate_flashcard_items(items, num_cards)
            if not ok:
                logger.warning(
                    "guard_fallback structured_output kind=flashcards reason=%s",
                    reason,
                )
                raise ValueError(f"Invalid flashcard structure: {reason}")

            flashcards = items[:num_cards]

            telemetry.log_metrics(
                {
                    "flashcards_generated": True,
                    "card_count": len(flashcards),
                    "source_content_length": len(content),
                }
            )
            return flashcards

        except Exception as e:
            logger.error("Error generating flashcards: %s", e)
            raise

    def get_similar_documents(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        document_ids: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        try:
            vector_store = Chroma(
                persist_directory=settings.chroma_persist_directory,
                embedding_function=self.embeddings,
                collection_name=collection_name,
            )
            k_fetch = (
                min(top_k * 5, settings.rag_top_k_max)
                if document_ids
                else top_k
            )
            results = vector_store.similarity_search_with_score(query, k=k_fetch)
            if document_ids:
                allowed = {str(i) for i in document_ids}
                results = [
                    (d, s)
                    for d, s in results
                    if d.metadata.get("document_id") in allowed
                ][:top_k]
            else:
                results = results[:top_k]

            similar_docs = []
            for doc, score in results:
                similar_docs.append(
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "similarity_score": float(score),
                    }
                )
            return similar_docs
        except Exception as e:
            logger.error("Error finding similar documents: %s", e)
            raise
