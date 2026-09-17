from app.models import Profile


def test_profile_model_has_required_fields():
    profile = Profile(
        full_name="Alex Morgan",
        headline="Analytics & Product Leader",
        summary="Builds data products with measurable business impact.",
        email="alex@example.com",
    )
    assert profile.full_name == "Alex Morgan"
    assert profile.headline == "Analytics & Product Leader"
