from textual import on
from textual.app import App
from textual.containers import ScrollableContainer
from textual.reactive import reactive
from textual.widgets import Header, Footer, Static, Button

class Alljobs(Static):
    """The page with all jobs."""

    def compose(self):
        yield Button("job", classes="job")

class Specificjob(Static):
    """The page with all trials of a job."""

    def compose(self):
        yield Button("essai", classes="essai")

class Joblog(App):
    """A log reader for DNAnexus"""

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ]

    CSS_PATH = "joblog.css"

    @on(Button.Pressed, ".job")
    def see_trials(self):
        self.add_class("started")
        self.query_one("#alljobs").add_class("hidden")
        self.query_one("#specificjob").remove_class("hidden")

    def compose(self):
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        with ScrollableContainer(id="alljobs"):
            yield Alljobs()
        with ScrollableContainer(id="specificjob", classes="hidden"):
            yield Specificjob()

    def action_toggle_dark(self):
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

if __name__ == "__main__":
    app = Joblog()
    app.run()
