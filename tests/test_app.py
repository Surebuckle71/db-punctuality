from streamlit.testing.v1 import AppTest

APP = "../app/streamlit_app.py"


def test_app_renders_default_view_without_errors():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert at.metric[1].label == "Net delay added at stations"


def test_app_handles_other_month_train_type_and_track_view():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.selectbox[0].select("2026-06").run()
    at.multiselect[0].set_value(["IC"]).run()
    at.radio[0].set_value("Track segments").run()
    assert not at.exception


def test_app_asks_for_a_train_type_when_none_selected():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.multiselect[0].set_value([]).run()
    assert not at.exception
    assert at.info[0].value == "Pick at least one train type."
