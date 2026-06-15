"""
End-to-end Playwright tests for the ResuméAI ATS Scorer Streamlit app.

Prerequisites:
    pip install pytest-playwright
    python -m playwright install chromium

Run (with app already running on localhost:8501):
    pytest tests/test_e2e.py --headed   # visible browser
    pytest tests/test_e2e.py            # headless
"""

import pytest
from playwright.sync_api import Page, expect


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BASE_URL = "http://localhost:8501"


@pytest.fixture(scope="session")
def base_url() -> str:
    """Return the base URL for the running Streamlit app."""
    return BASE_URL


@pytest.fixture()
def app_page(page: Page, base_url: str) -> Page:
    """Navigate to the app and wait for Streamlit to finish loading."""
    page.goto(base_url)
    # Wait until Streamlit's main content is rendered (the stApp element appears)
    page.wait_for_selector("[data-testid='stApp']", timeout=15_000)
    # Also wait for the network to be idle so all JS/CSS assets have loaded
    page.wait_for_load_state("networkidle", timeout=20_000)
    return page


# ---------------------------------------------------------------------------
# Sample data used across multiple tests
# ---------------------------------------------------------------------------

SAMPLE_RESUME = """
Jane Doe
jane.doe@example.com | linkedin.com/in/janedoe | github.com/janedoe

EXPERIENCE
Software Engineer — Acme Corp (2021–Present)
- Built RESTful APIs using Python and FastAPI, reducing latency by 30 %
- Led migration from monolith to microservices, improving deployment frequency
- Collaborated with cross-functional teams using Agile / Scrum methodology

Junior Developer — StartupXYZ (2019–2021)
- Developed React front-end components and integrated with GraphQL backends
- Automated CI/CD pipelines with GitHub Actions and Docker

SKILLS
Python, FastAPI, React, GraphQL, Docker, Kubernetes, PostgreSQL, AWS, Agile

EDUCATION
B.Sc. Computer Science — State University, 2019
"""

SAMPLE_JOB_DESC = """
Senior Software Engineer — Backend Focus

We are looking for a Senior Software Engineer to join our platform team.

Requirements:
- 3+ years of experience with Python and REST API development
- Experience with microservices architecture and Docker/Kubernetes
- Strong knowledge of PostgreSQL or similar relational databases
- Familiarity with AWS cloud services
- Excellent collaboration skills within Agile teams
- Experience with CI/CD pipelines (GitHub Actions preferred)

Nice to have:
- Experience with FastAPI or similar async frameworks
- GraphQL knowledge
"""


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _wait_for_streamlit_rerun(page: Page, timeout: int = 10_000) -> None:
    """
    After interacting with a Streamlit widget, wait for the app to re-run.
    Streamlit shows a running indicator; wait until it disappears.
    """
    # Streamlit renders a small status widget while re-running
    try:
        page.wait_for_selector(
            "[data-testid='stStatusWidget']",
            state="visible",
            timeout=3_000,
        )
        page.wait_for_selector(
            "[data-testid='stStatusWidget']",
            state="hidden",
            timeout=timeout,
        )
    except Exception:
        # If the indicator never appears the rerun was already instant — that's fine
        pass
    page.wait_for_load_state("networkidle", timeout=timeout)


def _fill_text_area(page: Page, label_text: str, content: str) -> None:
    """
    Type text into a Streamlit text_area identified by its visible label.
    Falls back to nth-of-type selection when label matching is ambiguous.
    """
    locator = page.get_by_label(label_text)
    locator.fill(content)


def _click_button(page: Page, button_text_fragment: str) -> None:
    """Click a Streamlit button whose visible text contains the given fragment."""
    page.locator("button").filter(has_text=button_text_fragment).first.click()


# ---------------------------------------------------------------------------
# Test group 1 — Page load & hero section
# ---------------------------------------------------------------------------

class TestPageLoad:
    """Verify the app loads and the hero section is fully rendered."""

    def test_page_title_in_browser_tab(self, app_page: Page) -> None:
        """Browser tab title should contain the app name."""
        expect(app_page).to_have_title(
            "ResuméAI — ATS Scorer",
            timeout=10_000,
        )

    def test_hero_title_visible(self, app_page: Page) -> None:
        """The hero heading text 'Smart Resume Scoring' is on screen."""
        hero_title = app_page.locator(".hero-title")
        expect(hero_title).to_be_visible(timeout=10_000)
        expect(hero_title).to_contain_text("Smart Resume Scoring")

    def test_hero_badge_visible(self, app_page: Page) -> None:
        """The 'AI-Powered Career Tool' badge renders inside the hero."""
        badge = app_page.locator(".hero-badge")
        expect(badge).to_be_visible()
        expect(badge).to_contain_text("AI-Powered Career Tool")

    def test_hero_subtitle_visible(self, app_page: Page) -> None:
        """The descriptive sub-headline is rendered."""
        sub = app_page.locator(".hero-sub")
        expect(sub).to_be_visible()
        expect(sub).to_contain_text("ATS match score")

    @pytest.mark.parametrize("step_label", [
        "Step 1",
        "Step 2",
    ])
    def test_step_labels_visible(self, app_page: Page, step_label: str) -> None:
        """Both column step-labels are present (Step 1 and Step 2)."""
        label = app_page.locator(".step-label").filter(has_text=step_label)
        expect(label.first).to_be_visible()

    def test_footer_visible(self, app_page: Page) -> None:
        """The branded footer is rendered at the bottom of the page."""
        footer = app_page.locator(".footer")
        expect(footer).to_be_visible()
        expect(footer).to_contain_text("ResuméAI")


# ---------------------------------------------------------------------------
# Test group 2 — Input widgets
# ---------------------------------------------------------------------------

class TestInputWidgets:
    """Verify all input widgets are present and interactive."""

    def test_file_uploader_visible(self, app_page: Page) -> None:
        """The file uploader element is on the page."""
        uploader = app_page.locator("[data-testid='stFileUploader']")
        expect(uploader.first).to_be_visible()

    def test_resume_text_area_visible(self, app_page: Page) -> None:
        """The resume text area (Step 1 column) is visible."""
        text_areas = app_page.locator("textarea")
        # There should be at least two text areas (resume + job desc)
        expect(text_areas.first).to_be_visible()

    def test_job_desc_text_area_visible(self, app_page: Page) -> None:
        """The job description text area (Step 2 column) is visible."""
        text_areas = app_page.locator("textarea")
        expect(text_areas).to_have_count(2, timeout=10_000)

    def test_resume_text_area_accepts_input(self, app_page: Page) -> None:
        """Typing into the resume text area updates its value."""
        resume_area = app_page.locator("textarea").nth(0)
        resume_area.fill("Software Engineer with 5 years of Python experience.")
        expect(resume_area).to_have_value(
            "Software Engineer with 5 years of Python experience."
        )

    def test_job_desc_text_area_accepts_input(self, app_page: Page) -> None:
        """Typing into the job description text area updates its value."""
        job_area = app_page.locator("textarea").nth(1)
        job_area.fill("Looking for a Python engineer with Django experience.")
        expect(job_area).to_have_value(
            "Looking for a Python engineer with Django experience."
        )


# ---------------------------------------------------------------------------
# Test group 3 — Analyse button
# ---------------------------------------------------------------------------

class TestAnalyseButton:
    """Verify the primary CTA button is rendered correctly."""

    def test_analyse_button_visible(self, app_page: Page) -> None:
        """The 'Analyse My Resume' button is visible on the page."""
        button = app_page.locator("button").filter(has_text="Analyse My Resume")
        expect(button.first).to_be_visible()

    def test_analyse_button_is_enabled(self, app_page: Page) -> None:
        """The 'Analyse My Resume' button is enabled (not disabled)."""
        button = app_page.locator("button").filter(has_text="Analyse My Resume").first
        expect(button).to_be_enabled()

    def test_analyse_button_has_primary_type(self, app_page: Page) -> None:
        """The analyse button carries the Streamlit primary kind attribute."""
        # Streamlit primary buttons include kind="primary" on the button element
        button = app_page.locator("button[kind='primary']").filter(
            has_text="Analyse My Resume"
        )
        expect(button.first).to_be_visible()


# ---------------------------------------------------------------------------
# Test group 4 — Empty-field validation
# ---------------------------------------------------------------------------

class TestEmptyFieldValidation:
    """
    Submitting with empty inputs must show a user-facing error.
    This test does NOT call the Groq API because the error fires before any
    AI call is made.
    """

    def test_error_shown_when_both_fields_empty(self, app_page: Page) -> None:
        """Clicking Analyse with no text shows a Streamlit error alert."""
        # Ensure fields are blank (fresh page already has blank fields)
        app_page.locator("textarea").nth(0).fill("")
        app_page.locator("textarea").nth(1).fill("")

        _click_button(app_page, "Analyse My Resume")
        _wait_for_streamlit_rerun(app_page)

        error_alert = app_page.locator("[data-testid='stAlert']").filter(
            has_text="Please provide both your resume and the job description"
        )
        expect(error_alert.first).to_be_visible(timeout=10_000)

    def test_error_shown_when_only_resume_filled(self, app_page: Page) -> None:
        """Clicking Analyse with only the resume filled still shows an error."""
        app_page.locator("textarea").nth(0).fill("I am a software engineer.")
        app_page.locator("textarea").nth(1).fill("")

        _click_button(app_page, "Analyse My Resume")
        _wait_for_streamlit_rerun(app_page)

        error_alert = app_page.locator("[data-testid='stAlert']").filter(
            has_text="Please provide both your resume and the job description"
        )
        expect(error_alert.first).to_be_visible(timeout=10_000)

    def test_error_shown_when_only_job_desc_filled(self, app_page: Page) -> None:
        """Clicking Analyse with only the job description filled shows an error."""
        app_page.locator("textarea").nth(0).fill("")
        app_page.locator("textarea").nth(1).fill("Looking for a Python developer.")

        _click_button(app_page, "Analyse My Resume")
        _wait_for_streamlit_rerun(app_page)

        error_alert = app_page.locator("[data-testid='stAlert']").filter(
            has_text="Please provide both your resume and the job description"
        )
        expect(error_alert.first).to_be_visible(timeout=10_000)

    def test_no_error_element_on_fresh_load(self, app_page: Page) -> None:
        """On initial load (before any submission) no error alert is present."""
        error_alerts = app_page.locator("[data-testid='stAlert']")
        # There should be zero error alerts when the page first loads
        expect(error_alerts).to_have_count(0, timeout=5_000)


# ---------------------------------------------------------------------------
# Test group 5 — Results section (requires Groq API; skip if unavailable)
# ---------------------------------------------------------------------------

class TestResultsSection:
    """
    Tests that exercise the full analyse flow.
    These tests call score_resume (pure Python, no AI) and verify the score
    ring, keyword counts, and section headings render correctly.

    The AI rewrite step (rewrite_bullets) calls Groq. If GROQ_API_KEY is not
    set in the environment the call will fail and Streamlit will show an error.
    We mark these tests with a custom marker so they can be skipped in CI when
    the key is absent.

    To run these in CI:
        GROQ_API_KEY=<key> pytest tests/test_e2e.py -m "with_groq"

    To skip AI tests:
        pytest tests/test_e2e.py -m "not with_groq"
    """

    @pytest.mark.with_groq
    def test_results_section_heading_appears(self, app_page: Page) -> None:
        """After a successful analyse, 'Your ATS Results' heading is visible."""
        app_page.locator("textarea").nth(0).fill(SAMPLE_RESUME)
        app_page.locator("textarea").nth(1).fill(SAMPLE_JOB_DESC)

        _click_button(app_page, "Analyse My Resume")
        # Allow generous timeout for AI response
        _wait_for_streamlit_rerun(app_page, timeout=60_000)

        results_heading = app_page.locator(".section-title").filter(
            has_text="Your ATS Results"
        )
        expect(results_heading.first).to_be_visible(timeout=60_000)

    @pytest.mark.with_groq
    def test_score_ring_visible_after_analyse(self, app_page: Page) -> None:
        """The ATS score ring SVG/div element renders after analysis."""
        app_page.locator("textarea").nth(0).fill(SAMPLE_RESUME)
        app_page.locator("textarea").nth(1).fill(SAMPLE_JOB_DESC)

        _click_button(app_page, "Analyse My Resume")
        _wait_for_streamlit_rerun(app_page, timeout=60_000)

        score_wrap = app_page.locator(".score-wrap")
        expect(score_wrap.first).to_be_visible(timeout=60_000)

    @pytest.mark.with_groq
    def test_score_percentage_is_numeric(self, app_page: Page) -> None:
        """The displayed ATS score contains a numeric percentage."""
        app_page.locator("textarea").nth(0).fill(SAMPLE_RESUME)
        app_page.locator("textarea").nth(1).fill(SAMPLE_JOB_DESC)

        _click_button(app_page, "Analyse My Resume")
        _wait_for_streamlit_rerun(app_page, timeout=60_000)

        score_num = app_page.locator(".score-num").first
        expect(score_num).to_be_visible(timeout=60_000)
        score_text = score_num.inner_text()
        # Text is like "72%" — strip % and assert it's an integer
        assert score_text.strip().rstrip("%").isdigit(), (
            f"Expected a numeric score percentage, got: {score_text!r}"
        )

    @pytest.mark.with_groq
    def test_matched_keywords_card_visible(self, app_page: Page) -> None:
        """The 'Keywords Matched' metric card is rendered."""
        app_page.locator("textarea").nth(0).fill(SAMPLE_RESUME)
        app_page.locator("textarea").nth(1).fill(SAMPLE_JOB_DESC)

        _click_button(app_page, "Analyse My Resume")
        _wait_for_streamlit_rerun(app_page, timeout=60_000)

        matched_card = app_page.locator(".met-lbl").filter(has_text="Keywords Matched")
        expect(matched_card.first).to_be_visible(timeout=60_000)

    @pytest.mark.with_groq
    def test_missing_keywords_card_visible(self, app_page: Page) -> None:
        """The 'Keywords Missing' metric card is rendered."""
        app_page.locator("textarea").nth(0).fill(SAMPLE_RESUME)
        app_page.locator("textarea").nth(1).fill(SAMPLE_JOB_DESC)

        _click_button(app_page, "Analyse My Resume")
        _wait_for_streamlit_rerun(app_page, timeout=60_000)

        missing_card = app_page.locator(".met-lbl").filter(has_text="Keywords Missing")
        expect(missing_card.first).to_be_visible(timeout=60_000)

    @pytest.mark.with_groq
    def test_ai_rewritten_bullets_section_visible(self, app_page: Page) -> None:
        """The 'AI-Rewritten Bullet Points' section heading appears in results."""
        app_page.locator("textarea").nth(0).fill(SAMPLE_RESUME)
        app_page.locator("textarea").nth(1).fill(SAMPLE_JOB_DESC)

        _click_button(app_page, "Analyse My Resume")
        _wait_for_streamlit_rerun(app_page, timeout=60_000)

        bullets_heading = app_page.locator(".section-title").filter(
            has_text="AI-Rewritten Bullet Points"
        )
        expect(bullets_heading.first).to_be_visible(timeout=60_000)

    @pytest.mark.with_groq
    def test_rewrite_box_contains_text(self, app_page: Page) -> None:
        """The AI rewrite output box is present and non-empty."""
        app_page.locator("textarea").nth(0).fill(SAMPLE_RESUME)
        app_page.locator("textarea").nth(1).fill(SAMPLE_JOB_DESC)

        _click_button(app_page, "Analyse My Resume")
        _wait_for_streamlit_rerun(app_page, timeout=60_000)

        rewrite_box = app_page.locator(".rewrite-box").first
        expect(rewrite_box).to_be_visible(timeout=60_000)
        content = rewrite_box.inner_text()
        assert len(content.strip()) > 10, (
            "Rewrite box appears empty — expected AI-generated bullet points."
        )


# ---------------------------------------------------------------------------
# Test group 6 — Cover letter section (visible after results)
# ---------------------------------------------------------------------------

class TestCoverLetterSection:
    """
    Verify the Cover Letter Generator section and its buttons appear after
    a successful analyse run.
    """

    @pytest.mark.with_groq
    def test_cover_letter_section_heading_visible(self, app_page: Page) -> None:
        """'Cover Letter Generator' heading appears in the results page."""
        app_page.locator("textarea").nth(0).fill(SAMPLE_RESUME)
        app_page.locator("textarea").nth(1).fill(SAMPLE_JOB_DESC)

        _click_button(app_page, "Analyse My Resume")
        _wait_for_streamlit_rerun(app_page, timeout=60_000)

        cl_heading = app_page.locator(".section-title").filter(
            has_text="Cover Letter Generator"
        )
        expect(cl_heading.first).to_be_visible(timeout=60_000)

    @pytest.mark.with_groq
    def test_generate_cover_letter_button_visible(self, app_page: Page) -> None:
        """The 'Generate Cover Letter' button is visible after results load."""
        app_page.locator("textarea").nth(0).fill(SAMPLE_RESUME)
        app_page.locator("textarea").nth(1).fill(SAMPLE_JOB_DESC)

        _click_button(app_page, "Analyse My Resume")
        _wait_for_streamlit_rerun(app_page, timeout=60_000)

        gen_button = app_page.locator("button").filter(
            has_text="Generate Cover Letter"
        )
        expect(gen_button.first).to_be_visible(timeout=60_000)

    @pytest.mark.with_groq
    def test_generate_cover_letter_button_is_enabled(self, app_page: Page) -> None:
        """The 'Generate Cover Letter' button is enabled and clickable."""
        app_page.locator("textarea").nth(0).fill(SAMPLE_RESUME)
        app_page.locator("textarea").nth(1).fill(SAMPLE_JOB_DESC)

        _click_button(app_page, "Analyse My Resume")
        _wait_for_streamlit_rerun(app_page, timeout=60_000)

        gen_button = app_page.locator("button").filter(
            has_text="Generate Cover Letter"
        ).first
        expect(gen_button).to_be_enabled(timeout=60_000)

    @pytest.mark.with_groq
    def test_download_cover_letter_button_appears_after_generation(
        self, app_page: Page
    ) -> None:
        """
        After clicking 'Generate Cover Letter', a 'Download Cover Letter'
        button (stDownloadButton) appears.
        """
        app_page.locator("textarea").nth(0).fill(SAMPLE_RESUME)
        app_page.locator("textarea").nth(1).fill(SAMPLE_JOB_DESC)

        _click_button(app_page, "Analyse My Resume")
        _wait_for_streamlit_rerun(app_page, timeout=60_000)

        _click_button(app_page, "Generate Cover Letter")
        _wait_for_streamlit_rerun(app_page, timeout=60_000)

        download_button = app_page.locator("[data-testid='stDownloadButton']")
        expect(download_button.first).to_be_visible(timeout=60_000)

    @pytest.mark.with_groq
    def test_cover_letter_content_renders(self, app_page: Page) -> None:
        """After generating, the cover letter text appears in a rewrite-box div."""
        app_page.locator("textarea").nth(0).fill(SAMPLE_RESUME)
        app_page.locator("textarea").nth(1).fill(SAMPLE_JOB_DESC)

        _click_button(app_page, "Analyse My Resume")
        _wait_for_streamlit_rerun(app_page, timeout=60_000)

        _click_button(app_page, "Generate Cover Letter")
        _wait_for_streamlit_rerun(app_page, timeout=60_000)

        # There should now be two rewrite-box elements: bullets + cover letter
        rewrite_boxes = app_page.locator(".rewrite-box")
        expect(rewrite_boxes).to_have_count(2, timeout=60_000)
        cover_letter_text = rewrite_boxes.nth(1).inner_text()
        assert len(cover_letter_text.strip()) > 50, (
            "Cover letter content appears empty."
        )


# ---------------------------------------------------------------------------
# Test group 7 — Parametrized edge cases
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("resume_text,job_text,expect_error", [
    # Both empty -> error
    ("", "", True),
    # Only resume -> error
    ("Experienced Python developer.", "", True),
    # Only job desc -> error
    ("", "We need a Python developer.", True),
    # Both present (no whitespace-only edge) -> no error shown immediately
    # (actual scoring happens, which may trigger AI; we just check no early error)
    ("Python developer with 3 years experience.", "Hiring Python developer.", False),
])
def test_empty_field_combinations(
    page: Page,
    base_url: str,
    resume_text: str,
    job_text: str,
    expect_error: bool,
) -> None:
    """
    Parametrized validation: various resume/job-desc combinations that
    should or should not trigger the empty-field error.
    """
    page.goto(base_url)
    page.wait_for_selector("[data-testid='stApp']", timeout=15_000)
    page.wait_for_load_state("networkidle", timeout=20_000)

    page.locator("textarea").nth(0).fill(resume_text)
    page.locator("textarea").nth(1).fill(job_text)

    page.locator("button").filter(has_text="Analyse My Resume").first.click()

    try:
        page.wait_for_selector("[data-testid='stStatusWidget']", state="visible", timeout=3_000)
        page.wait_for_selector("[data-testid='stStatusWidget']", state="hidden", timeout=30_000)
    except Exception:
        pass
    page.wait_for_load_state("networkidle", timeout=30_000)

    error_alert = page.locator("[data-testid='stAlert']").filter(
        has_text="Please provide both your resume and the job description"
    )

    if expect_error:
        expect(error_alert.first).to_be_visible(timeout=10_000)
    else:
        # When both fields are filled the error should NOT appear
        # (the AI call may fail if no Groq key, but the validation error won't show)
        expect(error_alert).to_have_count(0, timeout=10_000)


@pytest.mark.parametrize("widget_selector,expected_text", [
    (".hero-title", "Smart Resume Scoring"),
    (".hero-badge", "AI-Powered Career Tool"),
    (".hero-sub", "ATS match score"),
    (".footer", "ResuméAI"),
])
def test_static_content_parametrized(
    page: Page,
    base_url: str,
    widget_selector: str,
    expected_text: str,
) -> None:
    """
    Parametrized check that key static text elements are present and contain
    their expected content strings on a fresh page load.
    """
    page.goto(base_url)
    page.wait_for_selector("[data-testid='stApp']", timeout=15_000)
    page.wait_for_load_state("networkidle", timeout=20_000)

    element = page.locator(widget_selector)
    expect(element.first).to_be_visible(timeout=10_000)
    expect(element.first).to_contain_text(expected_text)
