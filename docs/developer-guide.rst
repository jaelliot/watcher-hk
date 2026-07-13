Developer Guide
===============

Watopnet is a `KERI <https://github.com/WebOfTrust/keri>`_ watcher service that monitors
Autonomic Identifiers (AIDs) and verifies key-event consistency across witnesses. Watchers
are provisioned dynamically via a management API, track observed AIDs, poll witnesses for
key state, and answer signed key-state queries from authorized controllers.

Environment
-----------

The current package metadata requires Python ``>=3.14.0``. Use Python ``3.14`` for
development and documentation work — this matches the Read the Docs build configuration.

Watopnet also requires ``libsodium``, which is a dependency of the ``keri`` package.

**macOS:**

.. code-block:: bash

   brew install libsodium

**Ubuntu/Debian:**

.. code-block:: bash

   sudo apt-get install libsodium-dev

Setup
-----

From the repository root:

.. code-block:: bash

   python3.14 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -e .

For development with test dependencies:

.. code-block:: bash

   python -m pip install -e ".[dev]"

End-to-End Walkthrough
----------------------

This section walks through the complete flow: starting a watcher, provisioning
it for a controller, registering a watched AID, and verifying key-state queries.
Follow these steps in order. If you get stuck, see the :ref:`troubleshooting` section.

.. note::

   Watchers depend on witnesses. The controller AID must already be incepted
   with witnesses before a watcher can monitor it. Start the witness service
   (``witopnet``) first — see the
   `witness-hk developer guide <https://github.com/keri-foundation/witness-hk>`_.

Step 1: Prepare the config directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a config directory with the KERI config file structure:

.. code-block:: bash

   mkdir -p /tmp/watcher-demo/keri/cf

   cat > /tmp/watcher-demo/keri/cf/watopnet.json <<'EOF'
   {
     "dt": "2024-01-01T00:00:00.000000+00:00",
     "watopnet": {
       "dt": "2024-01-01T00:00:00.000000+00:00",
       "curls": ["http://127.0.0.1:7632/"]
     }
   }
   EOF

.. note::

   ``--config-dir`` must point to ``/tmp/watcher-demo`` (one level *above*
   ``keri/``), not to ``/tmp/watcher-demo/keri/cf/``. KERI appends
   ``keri/cf/`` internally and looks for ``watopnet.json`` there.

Step 2: Start the watcher
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   watcher -H 7632 -t 7631 --config-dir /tmp/watcher-demo

Where ``-H`` is the main watcher HTTP port and ``-t`` is the boot server port.

You should see log output confirming both servers started:

.. code-block:: text

   Starting Watcher Operational Network
   listening internally: http/7631, externally: http/7632

Step 3: Verify liveness
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   curl -i http://127.0.0.1:7631/health

Expected: ``HTTP/1.1 204 No Content``

Step 4: Provision the watcher for your controller
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   curl -X POST http://127.0.0.1:7631/watchers \
     -H "Content-Type: application/json" \
     -d '{"aid": "<your-controller-aid>"}'

The response includes the watcher's endpoint identifier (``eid``) and OOBI URLs.

Step 5: Add a watched AID
~~~~~~~~~~~~~~~~~~~~~~~~~

Register an AID for the watcher to monitor:

.. code-block:: bash

   curl -X POST http://127.0.0.1:7632/watchers/<watcher-eid>/aids \
     -H "Content-Type: application/json" \
     -d '{"aid": "<target-aid>"}'

The watcher will begin polling witnesses for key state on this AID.

Step 6: Query key state
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   curl "http://127.0.0.1:7632/ksn?pre=<target-aid>"

Returns a signed key-state notice with the current key state and witness
endorsements.

Step 7: Check watcher status
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   curl "http://127.0.0.1:7632/watchers/<watcher-eid>/status"

Returns the watcher's current state including the controller AID, total
witnesses, and responsive witness count.

Architecture
------------

Watopnet runs two HTTP servers side by side:

- **Boot server** (default ``127.0.0.1:7631``): management API. Use this to provision
  new watchers (``POST /watchers``), delete watchers (``DELETE /watchers/{eid}``),
  and check liveness (``GET /health``).

- **Watcher server** (default ``127.0.0.1:7632``): KERI event processing. Handles
  event intake (``POST /``), OOBI resolution (``GET /oobi/...``), key-state
  queries (``GET /ksn``), and KEL replay (``GET /log``).

Each provisioned watcher gets its own non-transferable KERI identifier (Hab), its own
keystore, and its own mailbox. The :class:`~watopnet.app.watching.Watchery` class
manages all running watchers and persists their records in an LMDB database via
:class:`~watopnet.core.basing.Baser`.

Configuration
-------------

The watcher server is configured via a KERI config file. A sample is provided at
``scripts/keri/cf/watopnet.json``:

.. code-block:: json

   {
     "dt": "2022-01-20T12:57:59.823350+00:00",
     "watopnet": {
       "dt": "2022-01-20T12:57:59.823350+00:00",
       "curls": ["http://127.0.0.1:7632/"]
     }
   }

The ``curls`` field sets the controller URL(s) advertised by the watcher. Pass the
directory containing ``keri/cf/watopnet.json`` to ``--config-dir``.

Running the Watcher
-------------------

After installation, the ``watcher`` CLI is available:

.. code-block:: bash

   watcher -H 7632 -t 7631 --config-dir /path/to/scripts

Key flags:

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Flag
     - Default
     - Description
   * - ``-H`` / ``--http``
     - ``7632``
     - Port the watcher server listens on
   * - ``-t`` / ``--bootport``
     - ``7631``
     - Port the boot server listens on
   * - ``--config-dir`` / ``-c``
     - —
     - Directory one level above ``keri/cf/`` containing the config file
   * - ``--config-file``
     - —
     - Config filename override
   * - ``--loglevel``
     - ``INFO``
     - Log level: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``
   * - ``--logfile``
     - —
     - Path to write log output to file

Set ``DEBUG_WATCHER=1`` in your environment to print full tracebacks on errors.

Provisioning a Watcher
----------------------

To provision a new watcher for a controller AID, send a request to the boot server:

.. code-block:: bash

   curl -X POST http://127.0.0.1:7631/watchers \
        -H "Content-Type: application/json" \
        -d '{"aid": "<qb64-controller-aid>"}'

The response contains:

- ``cid``: the controller AID
- ``eid``: the watcher AID
- ``oobis``: list of OOBI URLs the controller should resolve

HTTP API Reference
------------------

.. _api-reference:

Boot server (``localhost:7631``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 30 60

   * - Method
     - Path
     - Description
   * - ``POST``
     - ``/watchers``
     - Provision a new watcher. Body: ``{"aid": "<qb64-AID>"}``
   * - ``DELETE``
     - ``/watchers/{eid}``
     - Delete a watcher by its endpoint identifier
   * - ``GET``
     - ``/health``
     - Liveness probe, returns ``204 No Content``

Watcher server (``localhost:7632``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 30 60

   * - Method
     - Path
     - Description
   * - ``POST``
     - ``/``
     - Submit a KERI event (KEL/EXN/TEL/QRY) with CESR attachments
   * - ``PUT``
     - ``/``
     - Push raw CESR bytes into the inbound stream
   * - ``POST``
     - ``/watchers/{eid}/aids``
     - Register an AID for the watcher to monitor
   * - ``GET``
     - ``/watchers/{eid}/status``
     - Get watcher status: controller AID, witness counts, watched AIDs
   * - ``GET``
     - ``/ksn``
     - Get the key state notice for a prefix
   * - ``GET``
     - ``/log``
     - Replay KEL events for a prefix
   * - ``GET``
     - ``/oobi/{aid}``
     - OOBI resolution endpoint
   * - ``GET``
     - ``/oobi/{aid}/{role}``
     - OOBI with role
   * - ``GET``
     - ``/oobi/{aid}/{role}/{eid}``
     - OOBI with role and participant EID

Testing
-------

.. code-block:: bash

   pip install -e ".[dev]"
   pytest tests/

Tests are located under ``tests/`` and cover the watcher lifecycle, OOBI
resolution, and key-state query paths. The test suite uses temporary in-memory
KERI keystores so no external services are required.

To run a specific test file:

.. code-block:: bash

   pytest tests/test_watching.py -v

.. _troubleshooting:

Troubleshooting
---------------

**"No such file or directory" when starting**
    Ensure ``--config-dir`` points one level *above* ``keri/``, not inside
    ``keri/cf/``. KERI looks for ``<config-dir>/keri/cf/watopnet.json``.

**Port already in use**
    Change ``-H`` or ``-t``. Both servers must bind to unique ports.
    Kill any existing ``watcher`` processes first: ``pkill -f watcher``.

**"Unknown sender key state" on provision**
    The controller AID must be incepted before provisioning. Run ``kli incept``
    first — see Step 4 in the End-to-End Walkthrough above.

**Watcher returns empty key state**
    The target AID must be registered with witnesses and have at least one
    key event before the watcher can query its state. Verify the witness is
    running and the AID has been incepted.

**ImportError: libsodium not found**
    Install libsodium: ``brew install libsodium`` (macOS) or
    ``sudo apt-get install libsodium-dev`` (Ubuntu/Debian).

**ModuleNotFoundError: No module named 'watopnet'**
    Install the package in development mode: ``pip install -e .`` from the
    repository root.

Building the Docs
-----------------

From the repository root:

.. code-block:: bash

   pip install -e .
   pip install sphinx sphinx-rtd-theme
   cd docs
   sphinx-build -b dirhtml . _build/html

To do a clean rebuild:

.. code-block:: bash

   rm -rf _build

Next: Witness
-------------

This watcher service is paired with ``witopnet`` (``witness-hk``), a KERI
witness that provides authenticated event receipting. Watchers depend on
witnesses for key-state verification. See the
`witness-hk repository <https://github.com/keri-foundation/witness-hk>`_
for its developer guide.
