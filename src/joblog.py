"""An app to read the logs of DNAnexus jobs."""

import argparse
import asyncio
import datetime
import re
import sys

from subprocess import Popen, PIPE

from textual import on
from textual.app import App
from textual.binding import Binding
from textual.containers import Center, HorizontalGroup, VerticalGroup
from textual.reactive import reactive
from textual.widgets import Button, Footer, Input, Log, ProgressBar, Static

class SearchBar(Input):
    """A search bar."""
    BINDINGS = [
        Binding("escape", "blur"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.can_focus = False

    def action_blur(self) -> None:
        """Unfocus search bar."""
        # Focus on first job viewed
        self.parent.query(Job).first().focus()

    def action_submit(self):
        """When a search is submitted."""
        self.action_blur()

        # Search for matches
        job_page = self.parent.query_one(JobPage)
        job_page.search = str(self.value)
        job_page.show_all_jobs()

class Job(Button):
    """A job."""

    def __init__(self,
                 jid: str,
                 jobname: str,
                 outputs: list,
                 runtime: str,
                 state: str,
                 user: str,
                 date: str,
                 **kwargs):
        self.jid = jid
        self.jobname = jobname
        self.outputs = outputs
        self.runtime = runtime
        self.state = state
        self.user = user
        self.date = date
        label = f"{jobname:^30s} | {date} | {runtime:^8} | {state:^7s} | {user:^15s}"
        super().__init__(label, **kwargs)

class JobPage(Static):
    """The page with all jobs."""

    n_jobs_shown = reactive(0)
    n_jobs_total = reactive(0)

    show_done = False
    show_running = False
    show_failed = False

    search = reactive("")

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
        # Remove everything
        data = self.query()
        if data: # If there's anything
            data.remove()

        # Get latest jobs
        command = ["dx", "find", "jobs", "-n", f"{self.n_jobs_total}", "--show-outputs"]
        if self.user:
            command += ["--user", f"{self.user}"]
        process = Popen(command, stdout=PIPE, stderr=PIPE)
        output, _ = process.communicate()

        if output:
            job_list = output.decode('utf-8').split("* ")[1:]
            if (job_list[-1]).startswith("More"):
                job_list = job_list[:-1]

            # For every job found
            for i, job in enumerate(job_list):
                sep = job.split()

                # Get positions
                parenthesis_info = [sep.index(info) for info in sep if info.startswith('(')]
                exec_id = parenthesis_info[0]

                # Get info
                jobname = " ".join(sep[:exec_id])
                # If the job is cached
                if jobname.startswith('['):
                    continue
                state = sep[parenthesis_info[1]].strip("()")
                jid = sep[parenthesis_info[1] + 1]
                user = sep[parenthesis_info[1] + 2]
                date = sep[parenthesis_info[1] + 3]
                date = datetime.datetime.strptime(date, '%Y-%m-%d').strftime('%d/%m/%y')
                runtime = "-"
                outputs = ""

                if state == "done":
                    if sep[sep.index('Output:')+1] != '-':
                        runtime = sep[parenthesis_info[2] + 1].strip("()")
                        output_start = sep.index('[')
                        output_end = sep.index(']')
                        for i in range(output_start + 1, output_end):
                            outputs += sep[i]
                        outputs = outputs.split(',')

                # Color
                if state == "done":
                    button_variant = "success"
                elif state == "failed":
                    button_variant = "error"
                elif state == "running":
                    button_variant = "primary"
                else:
                    button_variant = "default"

                # Add the job
                job_button = Job(jid=jid,
                                 jobname=jobname,
                                 outputs=outputs,
                                 runtime=runtime,
                                 state=state,
                                 user=user,
                                 date=date,
                                 variant=button_variant,
                                 classes="hidden")
                self.mount(job_button)

            # Add utilities
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
                    if job.state == "running":
                        job.remove_class("hidden")
                elif self.show_failed is True:
                    if job.state == "failed":
                        job.remove_class("hidden")
                else:
                    if self.search:
                        if (re.search(self.search, job.jobname) or
                            re.search(self.search, job.user) or
                            re.search(self.search, job.date)):
                            job.remove_class("hidden")
                        else:
                            job.add_class("hidden")
                    else:
                        job.remove_class("hidden")
            else:
                job.add_class("hidden")

    def hide_all_jobs(self):
        """Hide all jobs shown."""
        jobs = self.query(Job)
        for job in jobs:
            job.add_class("hidden")

    def show_all_jobs(self):
        """Show all jobs."""
        self.show_done = False
        self.show_running = False
        self.show_failed = False
        self.show_jobs()

    def watch_n_jobs_total(self):
        """When n_jobs_total changes."""
        self.read_job_log()

    def watch_n_jobs_shown(self):
        """When n_jobs_shown changes."""
        self.show_jobs()

    def watch_search(self):
        """When you search something."""
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

    # Hide palette keybind
    ENABLE_COMMAND_PALETTE = False

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
        ("s", "search_jobs", "Search"),
        ]

    CSS_PATH = "joblog.css"

    @on(Button.Pressed, "Job")
    def see_log(self, press):
        """Switch to the log page."""
        # Remove search bar
        search_bar = self.query_one(SearchBar)
        if "hidden" not in search_bar.classes:
            self.action_search_jobs()

        # Hide other pages
        job_container = self.query_one("#job_container")
        job_container.add_class("hidden")
        log_container = self.query_one("#log_container").remove_class("hidden")
        log_page = log_container.query_one(LogPage)
        log_page.outputs = press.button.outputs
        log_page.state = press.button.state

        # Hide download button if necessary
        log_page.outputs = press.button.outputs
        download_button = log_page.query_one(Button)
        if log_page.outputs:
            download_button.remove_class("hidden")
        else:
            download_button.add_class("hidden")

        # Show job log
        jid = press.button.jid
        command = ["dx", "watch", f"{jid}"]
        process = Popen(command, stdout=PIPE, stderr=PIPE)
        output, _ = process.communicate()
        log_text = output.decode('utf-8').strip()
        log = Log()
        log.write_line(log_text)
        log_page.mount(log)

    def __init__(self, *args, user: str, n_lines: int, step: int, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.n_lines = n_lines
        self.step = step

    def compose(self):
        """Create child widgets for the app."""
        yield SearchBar(placeholder="Press Enter to submit query.",
                        classes="hidden")
        with VerticalGroup(id="job_container"):
            yield JobPage(user=self.user,
                          n_lines=self.n_lines,
                          step=self.step
                          )
        with VerticalGroup(id="log_container", classes="hidden"):
            yield LogPage()
        yield Footer()

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

    def action_home(self):
        """An action to return to the main page."""
        # Empty and hide the log page
        log_container = self.query_one("#log_container")
        log_container.add_class("hidden")
        log_page = log_container.query_one(LogPage)
        log_page.query_one(Log).remove()

         # Show job page
        self.query_one("#job_container").remove_class("hidden")
        self.refresh_bindings()

    def action_show_all(self):
        """Show only done jobs."""
        job_page = self.query_one(JobPage)

        # Remove search
        job_page.search = ""
        search_bar = self.query_one(SearchBar)
        if "hidden" not in search_bar.classes:
            self.action_search_jobs()

        # Update page
        job_page.show_all_jobs()

    def action_show_done(self):
        """Show only done jobs."""
        job_page = self.query_one(JobPage)

        # Filters
        job_page.show_done = True
        job_page.show_running = False
        job_page.show_failed = False

        # Remove search
        job_page.search = ""
        search_bar = self.query_one(SearchBar)
        if "hidden" not in search_bar.classes:
            self.action_search_jobs()

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

        # Remove search
        job_page.search = ""
        search_bar = self.query_one(SearchBar)
        if "hidden" not in search_bar.classes:
            self.action_search_jobs()

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

        # Remove search
        job_page.search = ""
        search_bar = self.query_one(SearchBar)
        if "hidden" not in search_bar.classes:
            self.action_search_jobs()

        # Update page
        job_page.hide_all_jobs()
        job_page.show_jobs()

    def action_add_jobs(self):
        """Increase the number of jobs displayed."""
        self.query_one(JobPage).add_jobs()

    def action_remove_jobs(self):
        """Decrease the number of jobs displayed."""
        self.query_one(JobPage).remove_jobs()

    def action_search_jobs(self):
        """Open/close the search bar."""
        search_bar = self.query_one(SearchBar)
        search_bar.toggle_class("hidden")
        if "hidden" not in search_bar.classes:
            search_bar.can_focus = True
            search_bar.focus(scroll_visible=True)
        else:
            search_bar.can_focus = False
            search_bar.value = ""
            job_page = self.query_one(JobPage)
            job_page.search = ""

    def check_action(self, action: str, parameters: tuple[object, ...]):
        """Check if an action may run.

        Helps with hiding keybinds from specific pages.
        """
        no_job_binds = ["show_all", "show_done", "show_running",
                        "show_failed", "add_jobs", "remove_jobs",
                        "search_jobs"]
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
                        default=100,
                        type=int,
                        help="show n jobs"
                        )
    parser.add_argument('-s',
                        dest="step",
                        default=100,
                        type=int,
                        help="add/remove s jobs"
                        )

    # Arguments
    nargs = parser.parse_args()
    USER, NLINES, STEP = nargs.user, nargs.n_lines, nargs.step

    app = Joblog(user=USER, n_lines=NLINES, step=STEP)
    app.run()
