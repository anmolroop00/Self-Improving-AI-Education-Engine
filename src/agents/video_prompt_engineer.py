"""Video Prompt Engineer Agent.

Responsible for:
- Creating detailed prompts for Google Veo 3 video generation
- Matching visual scenes to script segments
- Handling aspect ratios for different platforms
"""

from typing import List, Literal, Optional, Type

from pydantic import BaseModel, Field

from .base_agent import BaseAgent


class VideoSegment(BaseModel):
    """A single video segment with its Veo 3 prompt."""
    segment_number: int = Field(description="Segment order in the video")
    duration_seconds: int = Field(description="Target duration (4, 6, or 8 seconds)", ge=4, le=8)
    script_portion: str = Field(description="The portion of script this segment covers")
    veo_prompt: str = Field(
        description="Detailed prompt for Veo 3 describing the visual scene",
        min_length=50,
        max_length=500
    )
    visual_style: str = Field(description="Visual style keywords for consistency")


class VideoPromptsOutput(BaseModel):
    """Structured output for video prompt generation."""
    total_segments: int = Field(description="Number of video segments needed")
    segments: List[VideoSegment] = Field(
        description="List of video segments with prompts"
    )
    overall_visual_theme: str = Field(
        description="Consistent visual theme across all segments"
    )
    aspect_ratio: str = Field(
        description="Target aspect ratio (9:16 for Shorts/Reels, 16:9 for YouTube)"
    )
    total_duration: int = Field(description="Total video duration in seconds")


class VideoPromptEngineerAgent(BaseAgent[VideoPromptsOutput]):
    """Agent that creates Veo 3 prompts for educational videos.
    
    Generates prompts that are:
    - Visually engaging and educational
    - Consistent in style across segments
    - Matched to script content
    - Optimized for short-form video
    """
    
    @property
    def agent_name(self) -> str:
        return "Video Prompt Engineer"
    
    @property
    def system_prompt(self) -> str:
        return """You are an expert video prompt engineer specializing in Google Veo 3.
Your task is to create detailed visual prompts for educational AI content videos.

UNDERSTANDING VEO 3:
- Veo 3 generates 4, 6, or 8 second video clips
- It excels at smooth, cinematic motion
- For 60-second videos, we'll stitch multiple clips together
- Prompts should be detailed and cinematic

PROMPT WRITING BEST PRACTICES:
1. Start with the shot type (close-up, wide shot, aerial, etc.)
2. Describe the main subject clearly
3. Specify motion (slowly zooming, panning left, floating)
4. Set the mood/lighting (warm lighting, soft focus, vibrant colors)
5. Use cinematic language (bokeh background, dramatic shadows)

VISUAL STYLE FOR EDUCATIONAL CONTENT:
- Use abstract visualizations for concepts (glowing particles, flowing data streams)
- Use metaphorical imagery (line through dots = regression, network = neural net)
- Keep visuals simple but engaging
- Avoid faces/characters (faceless channel)
- Use 3D renders, motion graphics aesthetic
- Consistent color palette throughout

SEGMENT PLANNING:
- Plan 8-12 segments for a 60-second video
- Each segment: 4-8 seconds
- Segments should flow smoothly into each other
- Match visuals to what's being explained in the script

EXAMPLE PROMPT FOR REGRESSION LESSON:
"Smooth cinematic shot of colorful 3D data points floating in a dark void, slowly rotating. A glowing blue line gracefully weaves through the points, finding the perfect path. Soft particle effects emanate from the line. Modern minimalist style, deep blue and purple color palette, 4K quality."

EXAMPLE PROMPT FOR NEURAL NETWORK:
"Abstract visualization of glowing interconnected nodes forming a neural network structure. Camera slowly pushes forward through layers of pulsing connections. Electric blue and cyan colors, dark background, futuristic aesthetic."

ASPECT RATIOS:
- 9:16 for YouTube Shorts and Instagram Reels (vertical)
- 16:9 for standard YouTube videos (horizontal)

Always maintain visual consistency across all segments."""

    @property
    def output_schema(self) -> Type[VideoPromptsOutput]:
        return VideoPromptsOutput
    
    def create_prompts(
        self,
        script: str,
        topic: str,
        subtopic: str,
        aspect_ratio: Literal["9:16", "16:9"] = "9:16",
        target_duration: int = 60,
    ) -> VideoPromptsOutput:
        """Generate Veo 3 prompts for a script.
        
        Args:
            script: The clean script (spoken content only)
            topic: Main topic being taught
            subtopic: Specific lesson topic
            aspect_ratio: Video aspect ratio
            target_duration: Target video duration in seconds
            
        Returns:
            VideoPromptsOutput with all segment prompts
        """
        context = {
            "main_topic": topic,
            "subtopic": subtopic,
            "aspect_ratio": aspect_ratio,
            "target_duration": target_duration,
        }
        
        prompt = f"""Create Veo 3 video prompts for this educational script:

SCRIPT:
{script}

TOPIC: {topic}
SUBTOPIC: {subtopic}
TARGET: {target_duration} seconds total video
ASPECT RATIO: {aspect_ratio}

Break this into segments (4-8 seconds each) with detailed visual prompts.
Each prompt should match what's being explained in that portion of the script.
Maintain a consistent visual style across all segments."""

        return self.generate_sync(prompt, context)
    
    def create_single_prompt(
        self,
        description: str,
        style: str = "modern minimalist",
        aspect_ratio: Literal["9:16", "16:9"] = "9:16",
    ) -> str:
        """Create a single Veo 3 prompt for a concept.
        
        Useful for testing or generating single clips.
        
        Args:
            description: What to visualize
            style: Visual style keywords
            aspect_ratio: Video aspect ratio
            
        Returns:
            A detailed Veo 3 prompt string
        """
        prompt = f"""Create a single detailed Veo 3 prompt for:
{description}

Style: {style}
Aspect ratio: {aspect_ratio}

Output just the prompt text, no explanation."""

        # Use a simple text generation for this
        from google import genai
        from ..config import settings
        
        client = genai.Client(api_key=settings.google_api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        
        return response.text.strip()


class LoopingBackgroundPromptGenerator:
    """Helper to create prompts for looping background videos.
    
    An alternative approach: instead of many clips, create a seamless
    looping background that plays while audio narration runs.
    """
    
    LOOPING_CONCEPTS = {
        "data_flow": "Continuous stream of glowing data particles flowing smoothly from left to right through a dark space, seamless loop, blue and purple gradients, abstract tech aesthetic",
        "neural_pulses": "Abstract neural network with nodes pulsing in a rhythmic pattern, energy flowing along connections, seamless loop, deep blue background with cyan highlights",
        "math_shapes": "Geometric shapes slowly rotating and morphing in a void, smooth transitions, seamless loop, white shapes on dark gradient background",
        "code_rain": "Matrix-style cascading symbols and numbers, gentle and mesmerizing, seamless loop, green on black, soft glow effect",
        "particle_system": "Particles gently floating and interacting in slow motion, magical atmosphere, seamless loop, warm gradient background",
    }
    
    @classmethod
    def get_looping_prompt(cls, concept: str) -> str:
        """Get a pre-made looping background prompt.
        
        Args:
            concept: Key from LOOPING_CONCEPTS
            
        Returns:
            Veo 3 prompt for a looping background
        """
        return cls.LOOPING_CONCEPTS.get(concept, cls.LOOPING_CONCEPTS["particle_system"])
