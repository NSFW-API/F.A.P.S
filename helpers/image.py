from pathlib import Path
from PIL import Image
from typing import Union, Tuple


def create_thumbnail(
    image_path: Union[str, Path],
    output_path: Union[str, Path],
    size: Tuple[int, int] = (256, 256),
    format: str = 'JPEG',
    quality: int = 85
) -> None:
    """
    Create a thumbnail from an original image.
    
    Args:
        image_path: Path to the original image
        output_path: Path where the thumbnail will be saved
        size: Target size (width, height) for the thumbnail
        format: Output image format (JPEG, PNG, etc.)
        quality: JPEG quality (0-100)
    """
    image_path = Path(image_path)
    output_path = Path(output_path)
    
    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Open the image
    with Image.open(image_path) as img:
        # Create a copy to avoid modifying the original
        thumb = img.copy()
        
        # Convert to RGB if needed (for formats like PNG with transparency)
        if thumb.mode in ['RGBA', 'P'] and format == 'JPEG':
            thumb = thumb.convert('RGB')
            
        # Resize to fit within the given size while maintaining aspect ratio
        thumb.thumbnail(size)
        
        # Save the thumbnail
        thumb.save(output_path, format=format, quality=quality)
