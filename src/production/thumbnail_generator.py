"""Thumbnail Generator Service.

Generates AI-powered thumbnails for videos using Google Imagen 3.
Creates visually appealing thumbnails with optional text overlay.
"""

import logging
from pathlib import Path
from typing import Optional
from uuid import uuid4

from google import genai
from google.genai import types

from ..config import settings

logger = logging.getLogger(__name__)


class ThumbnailGenerator:
    """Generate AI thumbnails using Imagen 3.
    
    Creates YouTube-optimized thumbnails (1280x720 or 1920x1080).
    Supports text overlay for titles.
    """
    
    # YouTube thumbnail dimensions
    THUMBNAIL_WIDTH = 1280
    THUMBNAIL_HEIGHT = 720
    
    def __init__(self):
        """Initialize Imagen 3 client."""
        self._client = genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
        )
        logger.info("Thumbnail generator initialized with Imagen 3")
    
    def generate(
        self,
        prompt: str,
        output_path: Optional[Path] = None,
        lesson_number: Optional[int] = None,
    ) -> Path:
        """Generate a thumbnail image.
        
        Args:
            prompt: Visual description for the thumbnail
            output_path: Where to save the image (optional)
            lesson_number: Lesson number for naming
            
        Returns:
            Path to the generated thumbnail
        """
        # Use effective output directory based on environment
        if output_path is None:
            thumbnails_dir = settings.effective_output_dir / "thumbnails"
            thumbnails_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"thumbnail_{lesson_number or uuid4().hex[:8]}.png"
            output_path = thumbnails_dir / filename
        
        logger.info(f"Generating thumbnail: {prompt[:50]}...")
        
        # Enhance prompt for thumbnail-style imagery
        enhanced_prompt = self._enhance_prompt(prompt)
        
        try:
            # Generate image using Imagen 3
            response = self._client.models.generate_images(
                model="imagen-3.0-generate-002",
                prompt=enhanced_prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="16:9",  # YouTube thumbnail ratio
                    output_mime_type="image/png",
                ),
            )
            
            if response.generated_images and len(response.generated_images) > 0:
                generated = response.generated_images[0]
                
                # Access the nested Image object
                image_obj = generated.image
                
                # Save the image
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Save using the Image object's save method or raw data
                if hasattr(image_obj, 'save'):
                    image_obj.save(str(output_path))
                elif hasattr(image_obj, 'image_bytes'):
                    with open(output_path, 'wb') as f:
                        f.write(image_obj.image_bytes)
                else:
                    # Try to get raw data from the image object
                    import base64
                    if hasattr(image_obj, 'data'):
                        with open(output_path, 'wb') as f:
                            f.write(base64.b64decode(image_obj.data))
                    else:
                        raise Exception("Cannot extract image data from generated image")
                
                logger.info(f"Thumbnail saved to {output_path}")
                return output_path
            else:
                raise Exception("No image was generated")
                
        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}")
            raise
    
    def _enhance_prompt(self, prompt: str) -> str:
        """Enhance prompt for better thumbnail generation.
        
        Args:
            prompt: Original prompt
            
        Returns:
            Enhanced prompt with thumbnail-specific styling
        """
        # Add thumbnail-specific instructions
        enhancements = [
            "high quality digital art",
            "vibrant colors",
            "eye-catching composition",
            "clean and modern style",
            "professional YouTube thumbnail style",
            "bold and dynamic",
            "no text or watermarks",
        ]
        
        enhanced = f"{prompt}. {', '.join(enhancements)}"
        return enhanced
    
    def generate_from_lesson(
        self,
        title: str,
        topic: str,
        lesson_number: int,
        script_summary: Optional[str] = None,
    ) -> Path:
        """Generate thumbnail based on lesson content.
        
        Args:
            title: Lesson title
            topic: Main topic
            lesson_number: Lesson number
            script_summary: Brief summary of script content
            
        Returns:
            Path to generated thumbnail
        """
        # Create a visual prompt from lesson info
        visual_elements = []
        
        # Add topic-specific visuals
        topic_lower = topic.lower()
        if "regression" in topic_lower or "line" in topic_lower:
            visual_elements.append("colorful data points and trend lines")
            visual_elements.append("graphs and charts")
        elif "neural" in topic_lower or "network" in topic_lower:
            visual_elements.append("glowing neural network visualization")
            visual_elements.append("connected nodes and pathways")
        elif "ai" in topic_lower or "artificial" in topic_lower:
            visual_elements.append("futuristic AI robot or brain")
            visual_elements.append("digital circuits and technology")
        else:
            visual_elements.append("educational illustration")
            visual_elements.append("modern tech visuals")
        
        # Build the prompt
        prompt = f"Thumbnail image for educational video about {title}. "
        prompt += f"Visual style: {', '.join(visual_elements)}. "
        prompt += "Background: gradient from dark blue to purple. "
        prompt += "Style: Bold, vibrant, engaging for young learners."
        
        if script_summary:
            prompt += f" Related to: {script_summary[:100]}"
        
        return self.generate(prompt, lesson_number=lesson_number)


def create_thumbnail_generator() -> ThumbnailGenerator:
    """Factory function to create thumbnail generator.
    
    Returns:
        ThumbnailGenerator instance
    """
    return ThumbnailGenerator()
