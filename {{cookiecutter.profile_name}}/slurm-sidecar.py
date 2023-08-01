#!/usr/bin/env python3
"""Run a Snakemake v7+ sidecar process for Slurm

This sidecar process will poll ``squeue --user [user] --format='%i,%T'``
every 60 seconds by default (use environment variable
``SNAKEMAKE_SLURM_SQUEUE_WAIT`` for adjusting this).

Note that you have to adjust the value to fit to your ``MinJobAge`` Slurm
configuration.  Jobs remain at least ``MinJobAge`` seconds known to the
Slurm controller (default of 300 seconds).  If you query ``squeue`` every
60 seconds then this is plenty and you will observe all relevant job status
states as they are relevant for Snakemake.

If the environment variable ``SNAKEMAKE_CLUSTER_SIDECAR_VARS`` is set then
the ``slurm-status.py`` of the slurm profile will attempt to query this
sidecar process via HTTP.  As the sidecar process does not update its
cache in real-time, setting ``SNAKEMAKE_SLURM_SQUEUE_WAIT`` too large might
lead to Snakemake missing the "done" job state.  The defaults of
``SNAKEMAKE_SLURM_SQUEUE_WAIT=60`` and Slurm's ``MinJobAge=600`` work well
together and you will see all relevant job statuses.

If the sidecar is queried for a job ID that it has not seen yet then it will
perform a query to ``sacct`` such that it works well if Snakemake "resume
external job" feature.  The ``slurm-submit.py`` script of the Snakemake profile
will register all jobs via POST with this sidecar.
"""

import http.server
import json
import logging
import os
import subprocess
import sys
import signal
import time
import threading
import uuid

from CookieCutter import CookieCutter


#: Enables debug messages for slurm sidecar.
DEBUG = bool(int(os.environ.get("SNAKEMAKE_SLURM_DEBUG", "0")))
#: Enables HTTP request logging in sidecar.
LOG_REQUESTS = bool(int(os.environ.get("SNAKEMAKE_SLURM_LOG_REQUESTS", "0")))
#: Command to call when calling squeue
SQUEUE_CMD = os.environ.get("SNAKEMAKE_SLURM_SQUEUE_CMD", "squeue")
#: Number of seconds to wait between ``squeue`` calls.
SQUEUE_WAIT = int(os.environ.get("SNAKEMAKE_SLURM_SQUEUE_WAIT", "60"))

logger = logging.getLogger(__name__)
if DEBUG:
    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.DEBUG)


class PollSqueueThread(threading.Thread):
    """Thread that polls ``squeue`` until stopped by ``stop()``"""

    def __init__(
        self,
        squeue_wait,
        squeue_cmd,
        squeue_timeout=2,
        sleep_time=0.01,
        max_tries=3,
        *args,
        **kwargs
    ):
        super().__init__(target=self._work, *args, **kwargs)
        #: Time to wait between squeue calls.
        self.squeue_wait = squeue_wait
        #: Command to call squeue with.
        self.squeue_cmd = squeue_cmd
        #: Whether or not the thread should stop.
        self.stopped = threading.Event()
        #: Previous call to ``squeue``
        self.prev_call = 0.0
        #: Time to sleep between iterations in seconds.  Thread can only be
        #: terminated after this interval when waiting.
        self.sleep_time = sleep_time
        #: Maximal running time to accept for call to ``squeue``.
        self.squeue_timeout = squeue_timeout
        #: Maximal number of tries if call to ``squeue`` fails.
        self.max_tries = max_tries
        #: Dict mapping the job id to the job state string.
        self.states = {}
        #: Make at least one call to squeue, must not fail.
        logger.debug("initializing trhead")
        self._call_squeue(allow_failure=False)
        self.prev_call = time.time()

    def _work(self):
        """Execute the thread's action"""
        while not self.stopped.is_set():
            now = time.time()
            if now - self.prev_call > self.squeue_wait:
                self._call_squeue()
                self.prev_call = now
            time.sleep(self.sleep_time)

    def get_state(self, jobid):
        """Return the job state for the given jobid."""
        jobid = str(jobid)
        if jobid not in self.states:
            try:
                self.states[jobid] = self._get_state_sacct(jobid)
            except:
                return "__not_seen_yet__"
        return self.states.get(jobid, "__not_seen_yet__")

    def register_job(self, jobid):
        """Register job with the given ID."""
        self.states.setdefault(jobid, None)

    def _get_state_sacct(self, jobid):
        """Implement retrieving state via sacct for resuming jobs."""
        cluster = CookieCutter.get_cluster_option()
        cmd = ["sacct", "-P", "-b", "-j", jobid, "-n"]
        if cluster:
            cmd.append(cluster)
        try_num = 0
        while try_num < self.max_tries:
            try_num += 1
            try:
                logger.debug("Calling %s (try %d)", cmd, try_num)
                output = subprocess.check_output(cmd, timeout=self.squeue_timeout, text=True)
            except subprocess.TimeoutExpired as e:
                logger.warning("Call to %s timed out (try %d of %d)", cmd, try_num, self.max_tries)
                continue
            except subprocess.CalledProcessError as e:
                logger.warning("Call to %s failed (try %d of %d)", cmd, try_num, self.max_tries)
                continue
            try:
                parsed = {x.split("|")[0]: x.split("|")[1] for x in output.strip().split("\n")}
                logger.debug("Returning state of %s as %s", jobid, parsed[jobid])
                return parsed[jobid]
            except IndexError:
                logger.warning("Could not parse %s (try %d of %d)", repr(output), try_num, self.max_tries)
            secs = try_num / 2.0
            loger.info("Sleeping %f seconds", secs)
            time.sleep(secs)
        raise Exception("Problem with call to %s" % cmd)

    def stop(self):
        """Flag thread to stop execution"""
        logger.debug("stopping thread")
        self.stopped.set()

    def _call_squeue(self, allow_failure=True):
        """Run the call to ``squeue``"""
        cluster = CookieCutter.get_cluster_option()
        try_num = 0
        cmd = [SQUEUE_CMD, "--user={}".format(os.environ.get("USER")), "--format=%i,%T", "--state=all"]
        if cluster:
            cmd.append(cluster)
        while try_num < self.max_tries:
            try_num += 1
            try:
                logger.debug("Calling %s (try %d)", cmd, try_num)
                output = subprocess.check_output(cmd, timeout=self.squeue_timeout, text=True)
                logger.debug("Output is:\n---\n%s\n---", output)
                break
            except subprocess.TimeoutExpired as e:
                if not allow_failure:
                    raise
                logger.debug("Call to %s timed out (try %d of %d)", cmd, try_num, self.max_tries)
            except subprocess.CalledProcessError as e:
                if not allow_failure:
                    raise
                logger.debug("Call to %s failed (try %d of %d)", cmd, try_num, self.max_tries)
        if try_num >= self.max_tries:
            logger.debug("Giving up for this round")
        else:
            logger.debug("parsing output")
            self._parse_output(output)

    def _parse_output(self, output):
        """Parse output of ``squeue`` call."""
        header = None
        for line in output.splitlines():
            line = line.strip()
            arr = line.split(",")
            if not header:
                if not line.startswith("JOBID"):
                    continue  # skip leader
                header = arr
            else:
                logger.debug("Updating state of %s to %s", arr[0], arr[1])
                self.states[arr[0]] = arr[1]


class JobStateHttpHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler class that responds to ```/job/status/${jobid}/`` GET requests"""

    def do_GET(self):
        """Only to ``/job/status/${job_id}/?``"""
        logger.debug("--- BEGIN GET")
        # Remove trailing slashes from path.
        path = self.path
        while path.endswith("/"):
            path = path[:-1]
        # Ensure that /job/status was requested
        if not self.path.startswith("/job/status/"):
            self.send_response(400)
            self.end_headers()
            return
        # Ensure authentication bearer is correct
        auth_required = "Bearer %s" % self.server.http_secret
        auth_header = self.headers.get("Authorization")
        logger.debug(
            "Authorization header is %s, required: %s" % (repr(auth_header), repr(auth_required))
        )
        if auth_header != auth_required:
            self.send_response(403)
            self.end_headers()
            return
        # Otherwise, query job ID status
        job_id = self.path[len("/job/status/") :]
        try:
            job_id=job_id.split("%20")[3]
        except IndexError:
            pass
        logger.debug("Querying for job ID %s" % repr(job_id))
        status = self.server.poll_thread.get_state(job_id)
        logger.debug("Status: %s" % status)
        if not status:
            self.send_response(404)
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            output = json.dumps({"status": status})
            logger.debug("Sending %s" % repr(output))
            self.wfile.write(output.encode("utf-8"))
        logger.debug("--- END GET")

    def do_POST(self):
        """Handle POSTs (only to ``/job/register/${job_id}/?``)"""
        logger.debug("--- BEGIN POST")
        # Remove trailing slashes from path.
        path = self.path
        while path.endswith("/"):
            path = path[:-1]
        # Ensure that /job/register was requested
        if not self.path.startswith("/job/register/"):
            self.send_response(400)
            self.end_headers()
            return
        # Ensure authentication bearer is correct
        auth_required = "Bearer %s" % self.server.http_secret
        auth_header = self.headers.get("Authorization")
        logger.debug(
            "Authorization header is %s, required: %s", repr(auth_header), repr(auth_required)
        )
        # Otherwise, register job ID
        job_id = self.path[len("/job/status/") :]
        self.server.poll_thread.register_job(job_id)
        self.send_response(200)
        self.end_headers()
        logger.debug("--- END POST")

    def log_request(self, *args, **kwargs):
        if LOG_REQUESTS:
            super().log_request(*args, **kwargs)


class JobStateHttpServer(http.server.HTTPServer):
    """The HTTP server class"""

    allow_reuse_address = False

    def __init__(self, poll_thread):
        """Initialize thread and print the ``SNAKEMAKE_CLUSTER_SIDECAR_VARS`` to stdout, then flush."""
        super().__init__(("0.0.0.0", 0), JobStateHttpHandler)
        #: The ``PollSqueueThread`` with the state dictionary.
        self.poll_thread = poll_thread
        #: The secret to use.
        self.http_secret = str(uuid.uuid4())
        sidecar_vars = {
            "server_port": self.server_port,
            "server_secret": self.http_secret,
            "pid": os.getpid(),
        }
        logger.debug(json.dumps(sidecar_vars))
        sys.stdout.write(json.dumps(sidecar_vars) + "\n")
        sys.stdout.flush()

    def log_message(self, *args, **kwargs):
        """Log messages are printed if ``DEBUG`` is ``True``."""
        if DEBUG:
            super().log_message(*args, **kwargs)


def main():
    # Start thread to poll ``squeue`` in a controlled fashion.
    poll_thread = PollSqueueThread(SQUEUE_WAIT, SQUEUE_CMD, name="poll-squeue")
    poll_thread.start()

    # Initialize HTTP server that makes available the output of ``squeue --user [user]``
    # in a controlled fashion.
    http_server = JobStateHttpServer(poll_thread)
    http_thread = threading.Thread(name="http-server", target=http_server.serve_forever)
    http_thread.start()

    # Allow for graceful shutdown of poll thread and HTTP server.
    def signal_handler(signum, frame):
        """Handler for Unix signals. Shuts down http_server and poll_thread."""
        logger.info("Shutting down squeue poll thread and HTTP server...")
        # from remote_pdb import set_trace
        # set_trace()
        poll_thread.stop()
        http_server.shutdown()
        logger.info("... HTTP server and poll thread shutdown complete.")
        for thread in threading.enumerate():
            logger.info("ACTIVE %s", thread.name)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Actually run the server.
    poll_thread.join()
    logger.debug("poll_thread done")
    http_thread.join()
    logger.debug("http_thread done")


if __name__ == "__main__":
    sys.exit(int(main() or 0))
