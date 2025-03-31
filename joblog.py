"""An app to read the logs of DNAnexus jobs."""

from subprocess import Popen, PIPE
from textual import on
from textual.app import App
from textual.containers import VerticalGroup, HorizontalGroup
from textual.reactive import reactive
from textual.widgets import Header, Footer, Static, Button, Log

INCR = 5

class Job(Button):
    """A job."""
    def __init__(self, label: str, jid: str, **kwargs):
        # Initialisation du bouton avec le label et l'id
        super().__init__(label, **kwargs)
        self.jid = jid

class Trial(Button):
    """A trial."""
    def __init__(self, label: str, jid: str, n_trial: str, **kwargs):
        # Initialisation du bouton avec le label et l'id
        super().__init__(label, **kwargs)
        self.jid = jid
        self.n_trial = n_trial

class JobPage(Static):
    """The page with all jobs."""

    n_jobs = reactive(INCR)

    @on(Button.Pressed, "#more")
    def add_jobs(self):
        """Increase the number of jobs displayed."""
        # Only if we're on the job page
        if not "hidden" in self.parent.classes:
            self.n_jobs += INCR
        self.parent.query_one("#less").disabled = False

    @on(Button.Pressed, "#less")
    def remove_jobs(self):
        """Decrease the number of jobs displayed."""
        # Only if we're on the job page
        if not "hidden" in self.parent.classes:
            # And there are enough jobs to remove
            if self.n_jobs > INCR:
                self.n_jobs -= INCR

    def read_job_log(self):
        """Create jobs from job log."""
        # Info des jobs
        command = ["dx", "find", "jobs", "-n", f"{self.n_jobs}"]
        process = Popen(command, stdout=PIPE, stderr=PIPE)
        output, _ = process.communicate()
        job_list = output.decode('utf-8').split("* ")[1:]
        if (job_list[-1]).startswith("More"):
            job_list = job_list[:-1]

        # Récupération des infos
        for job in job_list:
            sep = job.split()
            name = sep[0]
            state = sep[2].strip("()")
            jid = sep[3]
            user = sep[4]
            runtime = sep[-1].strip("()")
            # job_label = f"Name: {name} State: {state} Runtime: {runtime} User:{user}"
            job_label = f"{name:^30s} | {state:^7s} | {runtime:^8} | {user:^15s}"
            # Ajout des jobs
            if state == "done":
                button_variant = "success"
            elif state == "failed":
                button_variant = "error"
            else:
                button_variant = "warning"
            job_button = Job(label=job_label, jid=jid, variant=button_variant)
            self.mount(job_button)

        # Ajout de l'utilitaire pour le changement du nb de lignes
        change_line = HorizontalGroup(classes="change_line")
        button_more = Button("More", id="more")
        button_less = Button("Less", id="less")
        if self.n_jobs <= INCR:
            button_less.disabled = True
        self.mount(change_line)
        change_line.mount(button_more)
        change_line.mount(button_less)

    def watch_n_jobs(self):
        """When n_jobs changes."""
        # Efface tout
        data = self.query()
        if data: # s'il y a qqch
            data.remove()

        # Nouveaux jobs selon résultat du ls
        self.read_job_log()

class TrialPage(Static):
    """The page with all trials of a job."""

    def read_trial_log(self, jid):
        """Create trials from job."""
        # Ajout des trials
        working_trial = True
        n_trial = 0
        while working_trial is True:
            trial_command = ["dx", "watch", jid, "--try", str(n_trial)]
            process = Popen(trial_command, stdout=PIPE, stderr=PIPE)
            output, _ = process.communicate()
            if output:
                trial_button = Trial(f"Trial n°{n_trial + 1}",
                                     jid=jid,
                                     n_trial=n_trial,
                                     classes="fail")
                self.mount(trial_button)
                n_trial += 1
            else :
                working_trial = False

        # Coloration des boutons
        successful = self.query(Trial).last()
        successful.remove_class("fail")
        successful.add_class("successful")

class Joblog(App):
    """A log reader for DNAnexus."""

    BINDINGS = [
        ("h", "return_home", "Home"),
        ("b", "go_back", "Back"),
        ("r", "refresh", "Refresh"),
        ("d", "toggle_dark", "Toggle dark mode"),
        ]

    CSS_PATH = "joblog.css"

    @on(Button.Pressed, "Job")
    def see_trials(self, press):
        """Switch to the trials page."""
        # Hide other pages pages
        job_container = self.query_one("#job_container")
        job_container.add_class("hidden")
        trial_container = self.query_one("#trial_container").remove_class("hidden")

        # Create trials
        job_id = press.button.jid
        trial_container.query_one(TrialPage).read_trial_log(jid=job_id)

    @on(Button.Pressed, "Trial")
    def see_log(self, trial_button):
        """Switch to the log page."""
        # Switch pages
        trial_container = self.query_one("#trial_container")
        trial_container.add_class("hidden")
        log_container = self.query_one("#log_container").remove_class("hidden")

        # Remove previous log
        log_container.query_one(Log).remove()
        # Add new one
        n_trial = trial_button.button.n_trial
        jid = trial_button.button.jid
        command = ["dx", "watch", f"{jid}", "--try", f"{n_trial}"]
        process = Popen(command, stdout=PIPE, stderr=PIPE)
        output, err = process.communicate()
        log_text = output.decode('utf-8').strip()
        log = Log()
        log.write_line(log_text)
        log_container.mount(log)

    def compose(self):
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        with VerticalGroup(id="job_container"):
            yield JobPage()
        with VerticalGroup(id="trial_container", classes="hidden"):
            yield TrialPage()
        with VerticalGroup(id="log_container", classes="hidden"):
            yield Log()

    def action_return_home(self):
        """An action to return to the main page."""
        # Efface tous les trials
        trial_container = self.query_one("#trial_container")
        trials = trial_container.query(Trial)
        if trials: # s'il y en a
            trials.remove()
        trial_container.add_class("hidden")

        # Cache le log
        log_container = self.query_one("#log_container")
        log_container.add_class("hidden")

        # Réaffiche les jobs
        self.query_one("#job_container").remove_class("hidden")

    def action_go_back(self):
        """An action to return to the previous page."""
        job_container = self.query_one("#job_container")
        trial_container = self.query_one("#trial_container")
        log_container = self.query_one("#log_container")

        # Si on est sur la page de trials
        if not "hidden" in trial_container.classes:
            trials = trial_container.query(Trial)
            if trials: # s'il y en a
                trials.remove()
            trial_container.add_class("hidden")
            job_container.remove_class("hidden")

        # Si on est sur la page de log
        if not "hidden" in log_container.classes:
            log_container.add_class("hidden")
            trial_container.remove_class("hidden")

    def action_refresh(self):
        """Refresh page."""
        job_container = self.query_one("#job_container")
        trial_container = self.query_one("#trial_container")

        # Si on est sur la page de jobs
        if not "hidden" in job_container.classes:
            job_page = job_container.query_one(JobPage)
            data = job_page.query()
            if data: # s'il y a qqch
                data.remove()
            job_page.read_job_log()

        # Si on est sur la page de trials
        if not "hidden" in trial_container.classes:
            trial_page = trial_container.query_one(TrialPage)
            data = trial_page.query()
            jid = data.first(Trial).jid
            if data: # s'il y a qqch
                data.remove()
            trial_page.read_trial_log(jid)

    def action_toggle_dark(self):
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

if __name__ == "__main__":
    app = Joblog()
    app.run()
