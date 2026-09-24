from app.fieldproof.cloudinary_gw import url
from app.fieldproof.transforms import NamedTransform


def test_named_transform_url_fragments():
    thumb = url("sites/a", NamedTransform.THUMB)
    assert "c_fill" in thumb
    assert "g_auto" in thumb or "g_center" in thumb
    assert "w_320" in thumb and "h_240" in thumb

    analysis = url("sites/a", NamedTransform.ANALYSIS)
    assert "c_limit" in analysis and "w_1024" in analysis

    compare = url("sites/a", NamedTransform.COMPARE)
    assert "w_800" in compare and "h_600" in compare
    assert "e_blur_faces" in compare or "g_" in compare

    square = url("sites/a", NamedTransform.SQUARE)
    assert "w_1080" in square and "h_1080" in square

    story = url("sites/a", NamedTransform.STORY)
    assert "h_1920" in story

    frame = url("vid", NamedTransform.VIDEO_FRAME, resource_type="video", t=2, format="jpg")
    assert "so_2" in frame or "so_2.0" in frame
