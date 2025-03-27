from textual import on
from textual.app import App
from textual.containers import ScrollableContainer
from textual.reactive import reactive
from textual.widgets import Header, Footer, Static, Button

from subprocess import Popen, PIPE

INCR = 3

class Job(Button):
    """ A job. """
    pass

class Trial(Button):
    """ A trial. """
    pass

class Alljobs(Static):
    """The page with all jobs."""

    n_jobs = reactive(INCR)

    def read_job_log(self):
        """ Create jobs from job log. """
        # Info des jobs
        command = ["dx", "find", "jobs", "-n", f"{self.n_jobs}", "--brief"]
        process = Popen(command, stdout=PIPE, stderr=PIPE)
        output, _ = process.communicate()
        job_lists = output.decode('utf-8').split()

        # Ajout des jobs
        for job in job_lists:
            job_button = Job(f"{job}")
            self.mount(job_button)

    def watch_n_jobs(self):
        """ When n_jobs changes. """
        # Efface tous les jobs
        jobs = self.query(Job)
        if jobs: # s'il y en a
            jobs.remove()

        # Nouveaux jobs selon résultat du ls
        self.read_job_log()

class Specificjobs(Static):
    """The page with all trials of a job."""

    # Par défaut il sera vide pour pas overcrowder
    def compose(self):
        """temp"""
        yield Trial("test essai")

class Joblog(App):
    """A log reader for DNAnexus"""

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("+", "add_jobs", "View more"),
        ("-", "remove_jobs", "View less"),
        ("h", "return_home", "Home"),
        ]

    CSS_PATH = "joblog.css"

    @on(Job.Pressed)
    def see_trials(self):
        self.query_one("#job_panel").add_class("hidden")
        self.query_one("#trial_panel").remove_class("hidden")

    def compose(self):
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        with ScrollableContainer(id="job_panel"):
            yield Alljobs()
        with ScrollableContainer(id="trial_panel", classes="hidden"):
            yield Specificjobs()

    def action_toggle_dark(self):
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

    def action_return_home(self):
        """An action to return to the main page."""
        # Efface tous les trials
        trial_panel = self.query_one("#trial_panel")
        trials = trial_panel.query(Trial)
        if trials: # s'il y en a
            trials.remove()

        # Réaffiche les jobs
        self.query_one("#job_panel").remove_class("hidden")

    def action_add_jobs(self):
        """Increase the number of jobs displayed."""
        job_panel = self.query_one("#job_panel")
        # Only if we're on the job panel
        if not "hidden" in job_panel.classes:
            alljobs = job_panel.query_one(Alljobs)
            alljobs.n_jobs += INCR

    def action_remove_jobs(self):
        """Decrease the number of jobs displayed."""
        job_panel = self.query_one("#job_panel")
        # Only if we're on the job panel
        if not "hidden" in job_panel.classes:
            alljobs = job_panel.query_one(Alljobs)
            # And there are enough jobs to remove
            if alljobs.n_jobs > INCR:
                alljobs.n_jobs -= INCR

if __name__ == "__main__":
    app = Joblog()
    app.run()
