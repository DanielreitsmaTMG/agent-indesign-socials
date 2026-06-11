"""
Detecteert het gezicht in een foto met Apple's Vision-framework en geeft de positie ervan
terug als fractie (0-1) van de breedte/hoogte van de afbeelding, met (0,0) linksboven.
Wordt gebruikt om de foto in InDesign zo te positioneren dat het gezicht binnen het
PHOTO_FRAME blijft staan, ook nadat InDesign de foto proportioneel heeft bijgesneden om
het frame te vullen.

Bij meerdere gezichten wordt het grootste (dichtstbijzijnde) gezicht gebruikt.

Gebruik:
    python systems/smart_crop_photo.py <input_path>
"""

import sys

import Quartz
from Foundation import NSURL
import Vision


def detect_face_fraction(image_path):
    url = NSURL.fileURLWithPath_(image_path)
    source = Quartz.CGImageSourceCreateWithURL(url, None)
    if source is None:
        raise ValueError(f"Kan afbeelding niet lezen: {image_path}")

    image = Quartz.CGImageSourceCreateImageAtIndex(source, 0, None)

    request = Vision.VNDetectFaceRectanglesRequest.alloc().init()
    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(image, {})
    success, error = handler.performRequests_error_([request], None)

    if not success or error:
        raise RuntimeError(f"Vision-detectie mislukt: {error}")

    results = request.results()
    if not results:
        return None

    # Grootste gezicht (dichtstbijzijnde persoon) gebruiken
    best = max(results, key=lambda r: r.boundingBox().size.width * r.boundingBox().size.height)
    box = best.boundingBox()

    face_x = box.origin.x + box.size.width / 2
    # Vision gebruikt origin linksonder; wij willen fractie vanaf linksboven
    face_y = 1 - (box.origin.y + box.size.height / 2)

    return face_x, face_y


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    result = detect_face_fraction(sys.argv[1])
    print(result)
