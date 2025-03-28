from textual import on
from textual.app import App
from textual.containers import VerticalGroup, HorizontalGroup
from textual.reactive import reactive
from textual.widgets import Header, Footer, Static, Button

from subprocess import Popen, PIPE

INCR = 2

class Job(Button):
    """ A job. """
    def __init__(self, label: str, jid: str, **kwargs):
        # Initialisation du bouton avec le label et l'id
        super().__init__(label, **kwargs)
        self.jid = jid

class Trial(Button):
    """ A trial. """
    pass

class Log(Static):
    """The log of a trial."""
    pass

class JobPage(Static):
    """The page with all jobs."""

    n_jobs = reactive(INCR)

    @on(Button.Pressed, "#more")
    def add_jobs(self):
        """Increase the number of jobs displayed."""
        # Only if we're on the job page
        if not "hidden" in self.parent.classes:
            self.n_jobs += INCR

    @on(Button.Pressed, "#less")
    def remove_jobs(self):
        """Decrease the number of jobs displayed."""
        # Only if we're on the job page
        if not "hidden" in self.parent.classes:
            # And there are enough jobs to remove
            if self.n_jobs > INCR:
                self.n_jobs -= INCR

    def read_job_log(self):
        """ Create jobs from job log. """
        # Info des jobs
        command = ["dx", "find", "jobs", "-n", f"{self.n_jobs}", "--brief"]
        process = Popen(command, stdout=PIPE, stderr=PIPE)
        output, _ = process.communicate()
        job_lists = output.decode('utf-8').split()

        # Ajout des jobs
        for job in job_lists:
            job_button = Job(label=str(job), jid=f"{job}")
            self.mount(job_button)

        # Ajout de l'utilitaire pour le changement du nb de lignes
        change_line = HorizontalGroup(classes="change_line")
        button_more = Button("More", id="more")
        button_less = Button("Less", id="less")
        self.mount(change_line)
        change_line.mount(button_more)
        change_line.mount(button_less)

    def watch_n_jobs(self):
        """ When n_jobs changes. """
        # Efface tout
        data = self.query()
        if data: # s'il y a qqch
            data.remove()

        # Nouveaux jobs selon résultat du ls
        self.read_job_log()

class TrialPage(Static):
    """The page with all trials of a job."""

    def read_trial_log(self, jid):
        trial_list = list(range(3))

        # Ajout des trials
        for trial in trial_list:
            trial_button = Trial(f"{jid}-{trial + 1}")
            self.mount(trial_button)

class Joblog(App):
    """A log reader for DNAnexus"""

    BINDINGS = [
        ("h", "return_home", "Home"),
        ("b", "go_back", "Back"),
        # ("+", "add_jobs", "View more"),
        # ("-", "remove_jobs", "View less"),
        ("d", "toggle_dark", "Toggle dark mode"),
        ]

    CSS_PATH = "joblog.css"

    @on(Button.Pressed, "Job")
    def see_trials(self, press):
        # Switch pages
        job_page = self.query_one("#job_page")
        job_page.add_class("hidden")
        trial_page = self.query_one("#trial_page").remove_class("hidden")

        # Create trials
        job_id = press.button.jid
        trial_page.query_one(TrialPage).read_trial_log(jid=job_id)

    @on(Button.Pressed, "Trial")
    def see_log(self):
        # Switch pages
        trial_page = self.query_one("#trial_page")
        trial_page.add_class("hidden")
        log_page = self.query_one("#log_page").remove_class("hidden")

        # Remove previous log
        log_page.query_one(Log).remove()
        # Add new one
        log = Log("test log")
        log_page.mount(log)

        # Create trials
        # job_id = press.button.jid
        # trial_page.query_one(TrialPage).read_trial_log(jid=job_id)

    def compose(self):
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        with VerticalGroup(id="job_page"):
            yield JobPage()
        with VerticalGroup(id="trial_page", classes="hidden"):
            yield TrialPage()
        with VerticalGroup(id="log_page", classes="hidden"):
            yield Log()

    def action_return_home(self):
        """An action to return to the main page."""
        # Efface tous les trials
        trial_page = self.query_one("#trial_page")
        trials = trial_page.query(Trial)
        if trials: # s'il y en a
            trials.remove()
        trial_page.add_class("hidden")

        # Cache le log
        log_page = self.query_one("#log_page")
        log_page.add_class("hidden")

        # Réaffiche les jobs
        self.query_one("#job_page").remove_class("hidden")

    def action_go_back(self):
        """An action to return to the previous page."""
        job_page = self.query_one("#job_page")
        trial_page = self.query_one("#trial_page")
        log_page = self.query_one("#log_page")

        # Si on est sur la page de trials
        if not "hidden" in trial_page.classes:
            trials = trial_page.query(Trial)
            if trials: # s'il y en a
                trials.remove()
            trial_page.add_class("hidden")
            job_page.remove_class("hidden")

        # Si on est sur la page de log
        if not "hidden" in log_page.classes:
            log_page.add_class("hidden")
            trial_page.remove_class("hidden")

    # def action_add_jobs(self):
    #     """Increase the number of jobs displayed."""
    #     job_page = self.query_one("#job_page")
    #     # Only if we're on the job page
    #     if not "hidden" in job_page.classes:
    #         alljobs = job_page.query_one(JobPage)
    #         alljobs.n_jobs += INCR

    # def action_remove_jobs(self):
    #     """Decrease the number of jobs displayed."""
    #     job_page = self.query_one("#job_page")
    #     # Only if we're on the job page
    #     if not "hidden" in job_page.classes:
    #         alljobs = job_page.query_one(JobPage)
    #         # And there are enough jobs to remove
    #         if alljobs.n_jobs > INCR:
    #             alljobs.n_jobs -= INCR

    def action_toggle_dark(self):
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

if __name__ == "__main__":
    app = Joblog()
    app.run()
