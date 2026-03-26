import json
import logging
from typing import Any, Dict, List, Optional

import chromadb
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.schema import Document
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.config import settings
from app.services.document_processor import DocumentProcessor
from app import telemetry

logger = logging.getLogger(__name__)


def stamp_chunk_metadata(docs: List[Document], user_id: str, document_id: int) -> None:
    for doc in docs:
        meta = dict(doc.metadata) if doc.metadata else {}
        meta["document_id"] = str(document_id)
        meta["user_id"] = str(user_id)
        doc.metadata = meta


def _search_filter(document_ids: Optional[List[int]]) -> Optional[Dict[str, Any]]:
    if not document_ids:
        return None
    ids = [str(i) for i in document_ids]
    if len(ids) == 1:
        return {"document_id": ids[0]}
    return {"document_id": {"$in": ids}}


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
    ) -> Dict[str, Any]:
        try:
            vector_store = Chroma(
                persist_directory=settings.chroma_persist_directory,
                embedding_function=self.embeddings,
                collection_name=collection_name,
            )
            sk: Dict[str, Any] = {"k": top_k}
            flt = _search_filter(document_ids)
            if flt is not None:
                sk["filter"] = flt

            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=vector_store.as_retriever(search_kwargs=sk),
                return_source_documents=True,
            )

            result = qa_chain({"query": question})
            source_docs = []
            if result.get("source_documents"):
                for doc in result["source_documents"]:
                    source_docs.append(
                        {
                            "content": doc.page_content[:200] + "...",
                            "metadata": doc.metadata,
                        }
                    )

            response = {
                "answer": result["result"],
                "sources": source_docs,
                "question": question,
            }
            telemetry.log_metrics(
                {
                    "question_answered": True,
                    "question_length": len(question),
                    "answer_length": len(result["result"]),
                    "source_count": len(source_docs),
                    "filtered_documents": len(document_ids) if document_ids else 0,
                }
            )
            return response
        except Exception as e:
            logger.error("Error answering question: %s", e)
            raise

    def generate_quiz(self, content: str, num_questions: int = 5) -> List[Dict[str, Any]]:
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

            raw = response.content
            try:
                quiz_questions = json.loads(raw)
            except json.JSONDecodeError:
                start = raw.find("[")
                end = raw.rfind("]") + 1
                if start != -1 and end > start:
                    quiz_questions = json.loads(raw[start:end])
                else:
                    raise ValueError("Could not parse quiz questions from LLM response")

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

    def generate_flashcards(self, content: str, num_cards: int = 10) -> List[Dict[str, str]]:
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

            raw = response.content
            try:
                flashcards = json.loads(raw)
            except json.JSONDecodeError:
                start = raw.find("[")
                end = raw.rfind("]") + 1
                if start != -1 and end > start:
                    flashcards = json.loads(raw[start:end])
                else:
                    raise ValueError("Could not parse flashcards from LLM response")

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
