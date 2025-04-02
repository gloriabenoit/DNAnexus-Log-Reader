"""An app to read the logs of DNAnexus jobs."""

import sys
import argparse
import asyncio
from subprocess import Popen, PIPE
from textual import on
from textual.app import App
from textual.containers import VerticalGroup, HorizontalGroup, Center
from textual.reactive import reactive
from textual.widgets import Header, Footer, Static, Button, Log, ProgressBar

class Job(Button):
    """A job."""
    def __init__(self,
                 jid: str,
                 jobname: str,
                 state: str,
                 runtime: str,
                 user: str,
                 outputs: list,
                 **kwargs):
        # Initialisation du bouton avec le label et l'id
        self.jid = jid
        self.jobname = jobname
        self.state = state
        self.runtime = runtime
        self.user = user
        self.outputs = outputs
        label = f"{jobname:^30s} | {runtime:^8} | {state:^7s} | {user:^15s}"
        super().__init__(label, **kwargs)

class JobPage(Static):
    """The page with all jobs."""

    n_jobs_total = reactive(0)
    n_jobs_shown = reactive(0)
    show_done = False
    show_running = False
    show_failed = False

    @on(Button.Pressed, "#more")
    def add_jobs(self):
        """Increase the number of jobs displayed."""
        if self.n_jobs_shown + self.step > self.n_jobs_total:
            self.query_one("#more").remove()
            self.query_one("#less").remove()
            self.n_jobs_total *= 2
        self.n_jobs_shown += self.step
        self.parent.query_one("#less").disabled = False

    @on(Button.Pressed, "#less")
    def remove_jobs(self):
        """Decrease the number of jobs displayed."""
        # And there are enough jobs to remove
        if self.n_jobs_shown > self.step:
            self.n_jobs_shown -= self.step
        if self.n_jobs_shown <= self.step:
            self.parent.query_one("#less").disabled = True

    def __init__(self, *args, user: str, n_lines: int, step: int, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.n_lines = n_lines
        self.step = step

    def on_mount(self):
        """Update jobs on mount."""
        self.n_jobs_total = self.n_lines
        self.n_jobs_shown = self.n_lines

    def read_job_log(self):
        """Create jobs from job log."""
        # Efface tout
        data = self.query()
        if data: # s'il y a qqch
            data.remove()

        # Info des jobs
        command = ["dx", "find", "jobs", "-n", f"{self.n_jobs_total}", "--show-outputs"]
        if self.user:
            command += ["--user", f"{self.user}"]
        process = Popen(command, stdout=PIPE, stderr=PIPE)
        output, _ = process.communicate()

        if output:
            job_list = output.decode('utf-8').split("* ")[1:]
            if (job_list[-1]).startswith("More"):
                job_list = job_list[:-1]

            # Pour chaque job
            for i, job in enumerate(job_list):
                sep = job.split()
                # Info
                jobname = sep[0]
                state = sep[2].strip("()")
                jid = sep[3]
                user = sep[4]
                runtime = "-"
                outputs = ""
                if state == "done":
                    if sep[sep.index('Output:')+1] != '-':
                        runtime = sep[8].strip("()")
                        output_start = sep.index('[')
                        output_end = sep.index(']')
                        for i in range(output_start + 1, output_end):
                            outputs += sep[i]
                        outputs = outputs.split(',')

                # Coloration
                if state == "done":
                    button_variant = "success"
                elif state == "failed":
                    button_variant = "error"
                else:
                    button_variant = "warning"

                # Ajout du job
                job_button = Job(jid=jid,
                                 jobname=jobname,
                                 state=state,
                                 runtime=runtime,
                                 user=user,
                                 outputs=outputs,
                                 variant=button_variant,
                                 classes="hidden")
                self.mount(job_button)

            # Ajout de l'utilitaire pour le changement du nb de lignes
            change_line = HorizontalGroup(classes="change_line")
            button_more = Button("More", id="more")
            button_less = Button("Less", id="less")
            if self.n_jobs_total <= self.step:
                button_less.disabled = True
            self.mount(change_line)
            change_line.mount(button_more)
            change_line.mount(button_less)
        else:
            sys.exit("ERROR: Invalid user.\nPlease enter a valid user name.")

    def show_jobs(self):
        """View jobs."""
        # self.restart_count(total=False)
        jobs = self.query(Job)
        gap = 0
        if len(jobs) != self.n_jobs_total:
            gap = len(jobs) - self.n_jobs_total
        for i, job in enumerate(jobs):
            if i < gap:
                continue
            if i < self.n_jobs_shown + gap:
                if self.show_done is True:
                    if job.state == "done":
                        job.remove_class("hidden")
                elif self.show_running is True:
                    if (job.state != "done") and (job.state != "failed"):
                        job.remove_class("hidden")
                elif self.show_failed is True:
                    if job.state == "failed":
                        job.remove_class("hidden")
                else:
                    job.remove_class("hidden")
            else:
                job.add_class("hidden")
        # update_number = self.query("#number_jobs")
        # for job in update_number:
        #     job.update(f"{self.n_jobs_shown} out of {self.n_jobs_total} jobs.")

    def hide_all_jobs(self):
        """Hide all jobs shown."""
        jobs = self.query(Job)
        for job in jobs:
            job.add_class("hidden")

    def watch_n_jobs_total(self):
        """When n_jobs_total changes."""
        self.read_job_log()

    def watch_n_jobs_shown(self):
        """When n_jobs_shown changes."""
        self.show_jobs()

class LogPage(Static):
    """The page with the log."""

    @on(Button.Pressed, "#download")
    async def download_output(self):
        """Download the job output."""
        progress_bar = self.query_one(ProgressBar)
        progress_bar.update(total=len(self.outputs),
                            progress=0)
        progress_bar.remove_class("hidden")

        for output in self.outputs:
            command = ["dx", "download", f"{output}", "--overwrite"]
            process = Popen(command, stdout=PIPE, stderr=PIPE)
            await asyncio.to_thread(process.communicate)
            progress_bar.advance(1)

    def compose(self):
        """Log page components."""
        with Center():
            yield ProgressBar(total=10,
                              show_percentage=True,
                              show_eta=False,
                              classes="hidden")
        yield Button("Download", id="download")

class Joblog(App):
    """A log reader for DNAnexus."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("t", "refresh", "Toggle refresh"),
        ("h", "home", "Home"),
        ("a", "show_all", "All"),
        ("d", "show_done", "Done"),
        ("r", "show_running", "Running"),
        ("f", "show_failed", "Failed"),
        ("m", "add_jobs", "More"),
        ("l", "remove_jobs", "Less"),
        ]

    CSS_PATH = "joblog.css"

    @on(Button.Pressed, "Job")
    def see_log(self, press):
        """Switch to the log page."""
        # Hide other pages pages
        job_container = self.query_one("#job_container")
        job_container.add_class("hidden")
        log_container = self.query_one("#log_container").remove_class("hidden")
        log_page = log_container.query_one(LogPage)
        log_page.outputs = press.button.outputs
        log_page.state = press.button.state

        # Disable download button if necessary
        log_page.outputs = press.button.outputs
        download_button = log_page.query_one(Button)
        if log_page.outputs:
            download_button.disabled = False
        else:
            download_button.disabled = True

        # Add new one
        jid = press.button.jid
        command = ["dx", "watch", f"{jid}"]
        process = Popen(command, stdout=PIPE, stderr=PIPE)
        output, _ = process.communicate()
        log_text = output.decode('utf-8').strip()
        log = Log()
        log.write_line(log_text)
        log_page.mount(log)

    def __init__(self, *args, user: str, n_lines: int, step: int, **kwargs):
        self.user = user
        self.n_lines = n_lines
        self.step = step
        super().__init__(*args, **kwargs)

    def compose(self):
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        with VerticalGroup(id="job_container"):
            yield JobPage(user=self.user,
                          n_lines=self.n_lines,
                          step=self.step
                          )
        with VerticalGroup(id="log_container", classes="hidden"):
            yield LogPage()

    def action_home(self):
        """An action to return to the main page."""
        job_container = self.query_one("#job_container")

        # Si on est pas sur la page des jobs
        if "hidden" in job_container.classes:
            # Vide et cache le log
            log_container = self.query_one("#log_container")
            log_container.add_class("hidden")
            log_page = log_container.query_one(LogPage)
            log_page.query_one(Log).remove()

            # Réaffiche les jobs
            self.query_one("#job_container").remove_class("hidden")
        self.refresh_bindings()

    def action_quit(self):
        """An action to quit the app."""
        sys.exit()

    def action_refresh(self):
        """Refresh page."""
        job_container = self.query_one("#job_container")

        # Si on est sur la page de jobs
        if not "hidden" in job_container.classes:
            job_page = job_container.query_one(JobPage)
            job_page.read_job_log()
            job_page.show_jobs()

    def action_show_all(self):
        """Show only done jobs."""
        job_page = self.query_one(JobPage)

        # Reset all filters
        job_page.show_done = False
        job_page.show_running = False
        job_page.show_failed = False

        # Update page
        job_page.show_jobs()

    def action_show_done(self):
        """Show only done jobs."""
        job_page = self.query_one(JobPage)

        # Filters
        job_page.show_done = True
        job_page.show_running = False
        job_page.show_failed = False

        # Update page
        job_page.hide_all_jobs()
        job_page.show_jobs()

    def action_show_running(self):
        """Show only running/waiting jobs."""
        job_page = self.query_one(JobPage)

        # Filters
        job_page.show_done = False
        job_page.show_running = True
        job_page.show_failed = False

        # Update page
        job_page.hide_all_jobs()
        job_page.show_jobs()

    def action_show_failed(self):
        """Show only failed jobs."""
        job_page = self.query_one(JobPage)

        # Filters
        job_page.show_done = False
        job_page.show_running = False
        job_page.show_failed = True

        # Update page
        job_page.hide_all_jobs()
        job_page.show_jobs()

    def action_add_jobs(self):
        """Increase the number of jobs displayed."""
        self.query_one(JobPage).add_jobs()

    def action_remove_jobs(self):
        """Decrease the number of jobs displayed."""
        self.query_one(JobPage).remove_jobs()

    def check_action(self, action: str, parameters: tuple[object, ...]):
        """Check if an action may run."""
        no_job_binds = ["show_all", "show_done", "show_running",
                        "show_failed", "add_jobs", "remove_jobs"]
        no_log_binds = ["home"]

        if (action in no_log_binds and
            "hidden" not in self.query_one("#job_container").classes):
            return False
        if (action in no_job_binds and
            "hidden" not in self.query_one("#log_container").classes):
            return False
        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="DNAnexus Log Reader",
        description="Read DNAnexus job logs directly from the command line."
    )
    parser.add_argument('-u',
                        dest="user",
                        default="",
                        type=str,
                        help="show only jobs from said user"
                        )
    parser.add_argument('-n',
                        dest="n_lines",
                        default=10,
                        type=int,
                        help="show n jobs"
                        )
    parser.add_argument('-s',
                        dest="step",
                        default=5,
                        type=int,
                        help="add/remove s jobs"
                        )

    # Arguments
    nargs = parser.parse_args()
    USER, NLINES, STEP = nargs.user, nargs.n_lines, nargs.step

    app = Joblog(user=USER, n_lines=NLINES, step=STEP)
    app.run()
    sys.exit()
