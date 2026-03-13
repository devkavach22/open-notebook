import operator
from pathlib import Path
from typing import Any, Dict, List, Optional

from content_core import extract_content
from content_core.common import ProcessSourceState
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from loguru import logger
from typing_extensions import Annotated, TypedDict

from open_notebook.ai.models import Model, ModelManager
from open_notebook.domain.content_settings import ContentSettings
from open_notebook.domain.notebook import Asset, Source
from open_notebook.domain.transformation import Transformation
from open_notebook.graphs.transformation import graph as transform_graph


class SourceState(TypedDict):
    content_state: ProcessSourceState
    apply_transformations: List[Transformation]
    source_id: str
    notebook_ids: List[str]
    source: Source
    transformation: Annotated[list, operator.add]
    embed: bool


class TransformationState(TypedDict):
    source: Source
    transformation: Transformation


async def content_process(state: SourceState) -> dict:
    content_settings = ContentSettings(
        default_content_processing_engine_doc="auto",
        default_content_processing_engine_url="auto",
        default_embedding_option="ask",
        auto_delete_files="yes",
        youtube_preferred_languages=[
            "en",
            "pt",
            "es",
            "de",
            "nl",
            "en-GB",
            "fr",
            "hi",
            "ja",
        ],
    )
    content_state: Dict[str, Any] = state["content_state"]  # type: ignore[assignment]

    content_state["url_engine"] = (
        content_settings.default_content_processing_engine_url or "auto"
    )
    content_state["document_engine"] = (
        content_settings.default_content_processing_engine_doc or "auto"
    )
    content_state["output_format"] = "markdown"

    # Add speech-to-text model configuration from Default Models
    try:
        model_manager = ModelManager()
        defaults = await model_manager.get_defaults()
        if defaults.default_speech_to_text_model:
            stt_model = await Model.get(defaults.default_speech_to_text_model)
            if stt_model:
                content_state["audio_provider"] = stt_model.provider
                content_state["audio_model"] = stt_model.name
                logger.debug(
                    f"Using speech-to-text model: {stt_model.provider}/{stt_model.name}"
                )
    except Exception as e:
        logger.warning(f"Failed to retrieve speech-to-text model configuration: {e}")
        # Continue without custom audio model (content-core will use its default)

    # Check if we need to handle legacy Office files or archives before content-core processing
    file_path = content_state.get("file_path")
    
    if file_path:
        from open_notebook.processors.doc_processor import is_doc_file
        from open_notebook.processors.office_processor import is_legacy_office_file
        from open_notebook.processors.archive_processor import is_archive_file
        
        # Handle legacy .doc files
        if is_doc_file(file_path):
            try:
                from open_notebook.processors.doc_processor import extract_text_from_doc
                
                logger.info("Detected legacy .doc file, using custom processor")
                doc_text = extract_text_from_doc(file_path)
                
                from content_core.common import ProcessSourceState
                processed_state = ProcessSourceState(
                    content=doc_text,
                    url=None,
                    file_path=file_path,
                    title=Path(file_path).stem
                )
                logger.info(f"Extracted {len(doc_text)} characters from .doc file")
                
            except ImportError as e:
                logger.error(f".doc processor not available: {e}")
                raise ValueError(
                    "Unable to process .doc file. Please install antiword. "
                    "Run: apt-get install antiword (Linux) or brew install antiword (Mac)"
                )
            except Exception as e:
                logger.error(f".doc processing failed: {e}")
                raise ValueError(f"Failed to extract text from .doc file: {str(e)}")
        
        # Handle legacy Office files (.ppt, .xls)
        elif is_legacy_office_file(file_path):
            try:
                from open_notebook.processors.office_processor import extract_text_from_ppt, extract_text_from_xls
                
                office_type = is_legacy_office_file(file_path)
                logger.info(f"Detected legacy .{office_type} file, using custom processor")
                
                if office_type == 'ppt':
                    office_text = extract_text_from_ppt(file_path)
                else:  # xls
                    office_text = extract_text_from_xls(file_path)
                
                from content_core.common import ProcessSourceState
                processed_state = ProcessSourceState(
                    content=office_text,
                    url=None,
                    file_path=file_path,
                    title=Path(file_path).stem
                )
                logger.info(f"Extracted {len(office_text)} characters from .{office_type} file")
                
            except ImportError as e:
                logger.error(f"Office processor not available: {e}")
                raise ValueError(
                    f"Unable to process .{office_type} file. Please install catdoc. "
                    "Run: apt-get install catdoc (Linux) or brew install catdoc (Mac)"
                )
            except Exception as e:
                logger.error(f"Office file processing failed: {e}")
                raise ValueError(f"Failed to extract text from Office file: {str(e)}")
        
        # Handle archive files (.zip, .tar, .gz)
        elif is_archive_file(file_path):
            try:
                from open_notebook.processors.archive_processor import (
                    extract_archive, cleanup_temp_dir, get_processable_files
                )
                
                logger.info("Detected archive file, extracting contents")
                temp_dir, extracted_files = extract_archive(file_path)
                
                try:
                    # Filter to processable files
                    processable_files = get_processable_files(extracted_files)
                    
                    if not processable_files:
                        raise ValueError("No processable documents found in archive")
                    
                    # Process each file and combine content
                    combined_content = []
                    for extracted_file in processable_files[:20]:  # Limit to first 20 files
                        try:
                            file_content_state = {"file_path": extracted_file}
                            file_processed = await extract_content(file_content_state)
                            if file_processed.content:
                                combined_content.append(
                                    f"\n\n--- {Path(extracted_file).name} ---\n\n{file_processed.content}"
                                )
                        except Exception as e:
                            logger.warning(f"Failed to process {extracted_file}: {e}")
                    
                    if not combined_content:
                        raise ValueError("Failed to extract content from any files in archive")
                    
                    from content_core.common import ProcessSourceState
                    processed_state = ProcessSourceState(
                        content="\n".join(combined_content),
                        url=None,
                        file_path=file_path,
                        title=f"{Path(file_path).stem} (Archive - {len(combined_content)} files)"
                    )
                    logger.info(f"Extracted content from {len(combined_content)} files in archive")
                    
                finally:
                    # Always clean up temp directory
                    cleanup_temp_dir(temp_dir)
                    
            except Exception as e:
                logger.error(f"Archive processing failed: {e}")
                raise ValueError(f"Failed to process archive: {str(e)}")
        
        else:
            # Use content-core for all other file types
            processed_state = await extract_content(content_state)
    else:
        # No file path, use content-core (URL or text content)
        processed_state = await extract_content(content_state)

    # Check if we need to use Tesseract OCR for scanned PDFs
    if content_state.get("file_path") and content_state["file_path"].lower().endswith(".pdf"):
        try:
            from open_notebook.processors.tesseract_pdf import should_use_ocr, extract_text_from_scanned_pdf
            
            if should_use_ocr(content_state["file_path"], processed_state.content):
                logger.info("PDF appears to be scanned, using Tesseract OCR")
                ocr_text = extract_text_from_scanned_pdf(content_state["file_path"])
                if ocr_text and len(ocr_text.strip()) > len(processed_state.content or ""):
                    logger.info(f"Tesseract extracted {len(ocr_text)} chars vs {len(processed_state.content or '')} from standard extraction")
                    processed_state.content = ocr_text
        except ImportError:
            logger.warning("Tesseract OCR not available, install pytesseract and pdf2image")
        except Exception as e:
            logger.warning(f"Tesseract OCR failed, using standard extraction: {e}")

    if not processed_state.content or not processed_state.content.strip():
        url = processed_state.url or ""
        if url and ("youtube.com" in url or "youtu.be" in url):
            raise ValueError(
                "Could not extract content from this YouTube video. "
                "No transcript or subtitles are available. "
                "Try configuring a Speech-to-Text model in Settings "
                "to transcribe the audio instead."
            )
        raise ValueError(
            "Could not extract any text content from this source. "
            "The content may be empty, inaccessible, or in an unsupported format."
        )

    return {"content_state": processed_state}


async def save_source(state: SourceState) -> dict:
    content_state = state["content_state"]

    # Get existing source using the provided source_id
    source = await Source.get(state["source_id"])
    if not source:
        raise ValueError(f"Source with ID {state['source_id']} not found")

    # Update the source with processed content
    source.asset = Asset(url=content_state.url, file_path=content_state.file_path)
    source.full_text = content_state.content

    # Preserve existing title if none provided in processed content
    if content_state.title:
        source.title = content_state.title

    await source.save()

    # NOTE: Notebook associations are created by the API immediately for UI responsiveness
    # No need to create them here to avoid duplicate edges

    if state["embed"]:
        if source.full_text and source.full_text.strip():
            logger.debug("Embedding content for vector search")
            await source.vectorize()
        else:
            logger.warning(
                f"Source {source.id} has no text content to embed, skipping vectorization"
            )

    return {"source": source}


def trigger_transformations(state: SourceState, config: RunnableConfig) -> List[Send]:
    if len(state["apply_transformations"]) == 0:
        return []

    to_apply = state["apply_transformations"]
    logger.debug(f"Applying transformations {to_apply}")

    return [
        Send(
            "transform_content",
            {
                "source": state["source"],
                "transformation": t,
            },
        )
        for t in to_apply
    ]


async def transform_content(state: TransformationState) -> Optional[dict]:
    source = state["source"]
    content = source.full_text
    if not content:
        return None
    transformation: Transformation = state["transformation"]

    logger.debug(f"Applying transformation {transformation.name}")
    result = await transform_graph.ainvoke(
        dict(input_text=content, transformation=transformation)  # type: ignore[arg-type]
    )
    await source.add_insight(transformation.title, result["output"])
    return {
        "transformation": [
            {
                "output": result["output"],
                "transformation_name": transformation.name,
            }
        ]
    }


# Create and compile the workflow
workflow = StateGraph(SourceState)

# Add nodes
workflow.add_node("content_process", content_process)
workflow.add_node("save_source", save_source)
workflow.add_node("transform_content", transform_content)
# Define the graph edges
workflow.add_edge(START, "content_process")
workflow.add_edge("content_process", "save_source")
workflow.add_conditional_edges(
    "save_source", trigger_transformations, ["transform_content"]
)
workflow.add_edge("transform_content", END)

# Compile the graph
source_graph = workflow.compile()
