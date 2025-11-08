import base64
import os
import uuid
import logging
import sys
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent
from together import Together
from pydantic import Field

# Configure file-based logging for MCP stdio server
def setup_logging():
    """Setup file-based logging for MCP server since stdio is used for MCP protocol."""
    pid = os.getpid()
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    logger.handlers.clear()
    
    # Get AGENT_SHARED_DIR from environment
    agent_shared_dir = os.environ.get("AGENT_SHARED_DIR")
    if not agent_shared_dir:
        raise RuntimeError("AGENT_SHARED_DIR environment variable is not set")
    
    if not os.path.exists(agent_shared_dir):
        raise RuntimeError(f"AGENT_SHARED_DIR does not exist: {agent_shared_dir}")
    
    # Try AGENT_SHARED_DIR first, then fall back to /tmp/
    log_locations = [
        os.path.join(agent_shared_dir, f"mcp_together_image_gen_{pid}.log"),
        f"/tmp/mcp_together_image_gen_{pid}.log"
    ]
    
    for log_file in log_locations:
        try:
            file_handler = logging.FileHandler(log_file, mode='a')
            file_handler.setLevel(logging.INFO)
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            logger.addHandler(file_handler)
            logger.info(f"=== MCP Server Started (PID: {pid}, Log: {log_file}) ===")
            return logger
        except (PermissionError, OSError):
            continue
    
    # Fallback to stderr if all file logging attempts fail
    print(f"Failed to setup file logging in {agent_shared_dir} or /tmp/", file=sys.stderr)
    return logger

logger = setup_logging()

mcp = FastMCP("together-image-generation")
client = Together()
IMAGE2IMAGE_MODEL = os.environ["TOGETHER_IMAGE2IMAGE_MODEL_ID"]
IMAGE2TEXT_MODEL = os.environ["TOGETHER_IMAGE2TEXT_MODEL_ID"]
TEXT2IMAGE_MODEL = os.environ["TOGETHER_TEXT2IMAGE_MODEL_ID"]

def detect_image_type(b64string: str) -> str:
    """
    Detect the image type (e.g., 'png', 'jpeg', 'webp') by inspecting the decoded magic bytes.
    """
    # Decode enough bytes to check headers. Using 32 base64 chars -> 24 bytes.
    header_bytes = base64.b64decode(b64string[:32])
    
    # PNG: 8-byte signature
    if header_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    # JPEG: starts with 0xFF 0xD8 0xFF
    if header_bytes.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    # WebP: starts with 'RIFF' and contains 'WEBP' at offset 8
    if header_bytes.startswith(b"RIFF") and header_bytes[8:12] == b"WEBP":
        return "webp"
    return "png"  # default to png

@mcp.tool(description="Generate an image from a text description using Together AI.")
def generate_image(
    prompt: Annotated[str, Field(description="A text description of the desired image.")],
) -> ImageContent:
    logger.info(f"generate_image called - prompt: {prompt[:100]}... - model: {TEXT2IMAGE_MODEL}")
    
    try:
        response = client.images.generate(
            prompt=prompt,
            model=TEXT2IMAGE_MODEL,
            width=1024,
            height=1792,
            steps=4,
            n=1,
        )
        logger.info(f"API response received - images: {len(response.data)}")
        
        if not response.data:
            logger.warning("No images generated in response")
            raise ValueError("No images generated")

        case_id = uuid.uuid4().hex
        image = response.data[0]
        
        # Download the image from URL and convert to base64
        if image.url:
            import requests
            img_response = requests.get(image.url)
            image_base64 = base64.b64encode(img_response.content).decode('utf-8')
        elif image.b64_json:
            image_base64 = image.b64_json
        else:
            raise ValueError("No image data in response")
        
        output_format = detect_image_type(image_base64)
        result = ImageContent(
            type="image",
            data=image_base64,
            mimeType=f"image/{output_format}",
            annotations={"case_id": case_id, "prompt": prompt},
        )
        
        logger.info(f"generate_image completed - case_id: {case_id}")
        return result
    except Exception as e:
        logger.error(f"generate_image failed - error: {str(e)}", exc_info=True)
        raise

@mcp.tool(description="Edit or transform an image based on a text description using a reference image.")
def edit_image(
    image_path: Annotated[str, Field(description="The path to the image file to edit (use absolute path).")],
    prompt: Annotated[str, Field(description="A text description of how to edit/transform the image.")],
) -> ImageContent:
    logger.info(f"edit_image called - image_path: {image_path}, prompt: {prompt[:100]}... - model: {IMAGE2IMAGE_MODEL}")
    
    try:
        # Read and encode the image
        with open(image_path, "rb") as f:
            image_data = f.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        response = client.images.generate(
            prompt=prompt,
            model=IMAGE2IMAGE_MODEL,
            condition_image=image_base64,
            width=1024,
            height=1024,
            steps=4,
            n=1,
        )
        logger.info(f"API response received - images: {len(response.data)}")
        
        if not response.data:
            logger.warning("No images generated in response")
            raise ValueError("No images generated")

        case_id = uuid.uuid4().hex
        image = response.data[0]
        
        # Download the image from URL and convert to base64
        if image.url:
            import requests
            img_response = requests.get(image.url)
            result_base64 = base64.b64encode(img_response.content).decode('utf-8')
        elif image.b64_json:
            result_base64 = image.b64_json
        else:
            raise ValueError("No image data in response")
        
        output_format = detect_image_type(result_base64)
        result = ImageContent(
            type="image",
            data=result_base64,
            mimeType=f"image/{output_format}",
            annotations={"case_id": case_id, "prompt": prompt, "source_image": image_path},
        )
        
        logger.info(f"edit_image completed - case_id: {case_id}")
        return result
    except Exception as e:
        logger.error(f"edit_image failed - error: {str(e)}", exc_info=True)
        raise

@mcp.tool(description="Describe what's in an image using vision AI.")
def describe_image(
    image_path: Annotated[str, Field(description="The path to the image file to describe (use absolute path).")],
) -> str:
    logger.info(f"describe_image called - image_path: {image_path} - model: {IMAGE2TEXT_MODEL}")
    
    try:
        # Read and encode the image
        with open(image_path, "rb") as f:
            image_data = f.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Create a data URL for the image
        image_type = detect_image_type(image_base64)
        image_url = f"data:image/{image_type};base64,{image_base64}"
        
        # Use Together AI's vision model to describe the image
        response = client.chat.completions.create(
            model=IMAGE2TEXT_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": "Describe this image in detail."}
                    ]
                }
            ],
        )
        
        description = response.choices[0].message.content
        logger.info(f"describe_image completed - description length: {len(description)}")
        return description
    except Exception as e:
        logger.error(f"describe_image failed - error: {str(e)}", exc_info=True)
        raise

