from app.fieldproof.pipelines import _detection_tags


def test_detection_tags_parses_real_coco_v2_shape():
    detection = {
        "object_detection": {
            "status": "complete",
            "data": {
                "coco": {
                    "tags": {
                        "person": [{"confidence": 95.3, "boundingPoly": {}}],
                        "dog": [{"confidence": 40.0, "boundingPoly": {}}],
                    },
                    "status": "success",
                }
            },
        }
    }
    tags = dict(_detection_tags(detection))
    assert tags["person"] == 0.953
    assert "dog" not in tags  # below DETECTION_MIN_CONF (0.6)


def test_detection_tags_handles_empty_tags():
    detection = {"object_detection": {"data": {"coco": {"tags": {}}}}}
    assert _detection_tags(detection) == []


def test_detection_tags_fallback_shape():
    detection = {"raw": [{"tag": "car", "confidence": 88}]}
    tags = dict(_detection_tags(detection))
    assert tags["car"] == 0.88
