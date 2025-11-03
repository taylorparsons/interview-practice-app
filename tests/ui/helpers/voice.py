"""Utilities for stubbing realtime voice browser APIs during Helium tests."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


_INSTALL_STUBS_SCRIPT = """
(function (config) {
  const defaults = {
    sessionResponse: {
      ok: true,
      status: 200,
      body: {
        client_secret: 'test-secret',
        model: 'gpt-realtime-test',
        url: 'https://realtime.test/session'
      }
    },
    sdpResponse: {
      ok: true,
      status: 200,
      body: 'v=0\\ntest-answer'
    },
    memorizeResponse: {
      ok: true,
      status: 200,
      body: { saved: true }
    },
    personaResponse: {
      ok: true,
      status: 200,
      body: { updated: true }
    },
    transcriptResponse: {
      ok: true,
      status: 200,
      body: {}
    }
  };

  const original = {
    fetch: window.fetch,
    RTCPeerConnection: window.RTCPeerConnection,
    getUserMedia:
      (navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
      ? navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices)
      : null
  };

  const state = {
    config: Object.assign({}, defaults, config || {}),
    requests: [],
    channel: null,
    peer: null,
    flags: {
      channelClosed: false,
      peerClosed: false
    }
  };

  function buildResponse(definition) {
    const ok = definition && definition.ok !== false;
    const status = (definition && definition.status) || (ok ? 200 : 500);
    const body = definition ? definition.body : null;
    return {
      ok,
      status,
      json: async () => body,
      text: async () => (typeof body === 'string' ? body : JSON.stringify(body)),
    };
  }

  function recordFetch(url, init) {
    state.requests.push({
      url: url,
      method: (init && init.method) || 'GET',
      body: (init && init.body) || null,
      headers: (init && init.headers) || null,
    });
  }

  function fakeFetch(input, init) {
    const url = typeof input === 'string' ? input : (input && input.url) || '';
    recordFetch(url, init);

    const { sessionResponse, sdpResponse, memorizeResponse, personaResponse, transcriptResponse } = state.config;
    const realtimeBase = sessionResponse && sessionResponse.body && sessionResponse.body.url;

    if (url.includes('/voice/session')) {
      return Promise.resolve(buildResponse(sessionResponse));
    }
    if (realtimeBase && url.startsWith(realtimeBase)) {
      return Promise.resolve(buildResponse(sdpResponse));
    }
    if (url.includes('/voice-transcript/memorize')) {
      return Promise.resolve(buildResponse(memorizeResponse));
    }
    if (url.match(/\\/session\\/[^/]+\\/voice-transcript$/)) {
      return Promise.resolve(buildResponse(transcriptResponse));
    }
    if (url.includes('/coach')) {
      return Promise.resolve(buildResponse(personaResponse));
    }

    return original.fetch.call(window, input, init);
  }

  function FakeMediaStream() {
    this._tracks = [{ stop: function () {} }];
  }
  FakeMediaStream.prototype.getTracks = function () {
    return this._tracks.slice();
  };

  function FakeDataChannel(label) {
    this.label = label;
    this.readyState = 'connecting';
    this.onmessage = null;
    this.onopen = null;
    this.onclose = null;
    this._sent = [];
  }
  FakeDataChannel.prototype.send = function (payload) {
    this._sent.push(payload);
  };
  FakeDataChannel.prototype.close = function () {
    this.readyState = 'closed';
    state.flags.channelClosed = true;
    if (typeof this.onclose === 'function') {
      try { this.onclose(); } catch (err) {}
    }
  };
  FakeDataChannel.prototype._triggerOpen = function () {
    this.readyState = 'open';
    if (typeof this.onopen === 'function') {
      this.onopen();
    }
  };
  FakeDataChannel.prototype._emit = function (payload) {
    if (typeof this.onmessage === 'function') {
      const data = typeof payload === 'string' ? payload : JSON.stringify(payload);
      this.onmessage({ data });
    }
  };

  function FakePeerConnection() {
    state.peer = this;
    this.connectionState = 'new';
    this.localDescription = null;
    this.remoteDescription = null;
    this.onconnectionstatechange = null;
    this.onicecandidate = null;
    this.ontrack = null;
    this._tracks = [];
  }
  FakePeerConnection.prototype.createDataChannel = function (label) {
    const channel = new FakeDataChannel(label);
    state.channel = channel;
    return channel;
  };
  FakePeerConnection.prototype.addTrack = function (track, stream) {
    this._tracks.push({ track, stream });
  };
  FakePeerConnection.prototype.createOffer = function () {
    return Promise.resolve({ type: 'offer', sdp: 'v=0\\nfake-offer' });
  };
  FakePeerConnection.prototype.setLocalDescription = function (desc) {
    this.localDescription = desc;
    return Promise.resolve();
  };
  FakePeerConnection.prototype.setRemoteDescription = function (desc) {
    this.remoteDescription = desc;
    this.connectionState = 'connected';
    if (typeof this.onconnectionstatechange === 'function') {
      this.onconnectionstatechange();
    }
    return Promise.resolve();
  };
  FakePeerConnection.prototype.close = function () {
    this.connectionState = 'closed';
    state.flags.peerClosed = true;
    if (state.channel) {
      state.channel.close();
    }
    if (typeof this.onconnectionstatechange === 'function') {
      try { this.onconnectionstatechange(); } catch (err) {}
    }
  };

  window.fetch = fakeFetch;
  window.RTCPeerConnection = FakePeerConnection;

  if (!navigator.mediaDevices) {
    navigator.mediaDevices = {};
  }
  navigator.mediaDevices.getUserMedia = function () {
    return Promise.resolve(new FakeMediaStream());
  };

  window.__voiceTest = {
    setConfig(partial) {
      state.config = Object.assign({}, state.config, partial || {});
    },
    triggerDataChannelOpen() {
      if (state.channel) {
        state.channel._triggerOpen();
        return true;
      }
      return false;
    },
    emitDataChannelMessage(payload) {
      if (state.channel) {
        state.channel._emit(payload);
        return true;
      }
      return false;
    },
    getRequests() {
      return state.requests.slice();
    },
    clearRequests() {
      state.requests.length = 0;
    },
    getFlags() {
      return Object.assign({}, state.flags);
    },
    teardown() {
      window.fetch = original.fetch;
      if (original.RTCPeerConnection) {
        window.RTCPeerConnection = original.RTCPeerConnection;
      } else {
        delete window.RTCPeerConnection;
      }
      if (original.getUserMedia) {
        navigator.mediaDevices.getUserMedia = original.getUserMedia;
      } else if (navigator.mediaDevices) {
        delete navigator.mediaDevices.getUserMedia;
      }
      state.channel = null;
      state.peer = null;
      state.requests.length = 0;
      state.flags.channelClosed = false;
      state.flags.peerClosed = false;
      delete window.__voiceTest;
    }
  };
})(arguments[0]);
"""

_TEARDOWN_SCRIPT = """
if (window.__voiceTest && typeof window.__voiceTest.teardown === 'function') {
  window.__voiceTest.teardown();
}
"""


class VoiceTestController:
    """Convenience wrapper around the injected JS voice test harness."""

    def __init__(self, driver: Any):
        self.driver = driver
        self._installed = False

    def install(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Inject stubs into the browser context."""
        if self._installed:
            return
        self.driver.execute_script(_INSTALL_STUBS_SCRIPT, config or {})
        self._installed = True

    def teardown(self) -> None:
        """Restore original browser APIs."""
        if not self._installed:
            return
        self.driver.execute_script(_TEARDOWN_SCRIPT)
        self._installed = False

    def configure(self, **partial: Any) -> None:
        """Update stubbed responses."""
        self.driver.execute_script(
            "if (window.__voiceTest) { window.__voiceTest.setConfig(arguments[0]); }",
            partial,
        )

    def trigger_data_channel_open(self) -> bool:
        """Simulate the realtime data channel becoming ready."""
        return bool(
            self.driver.execute_script(
                "return window.__voiceTest && window.__voiceTest.triggerDataChannelOpen();"
            )
        )

    def emit_data_channel_message(self, payload: Dict[str, Any]) -> bool:
        """Inject an inbound realtime event payload."""
        return bool(
            self.driver.execute_script(
                "return window.__voiceTest && window.__voiceTest.emitDataChannelMessage(arguments[0]);",
                payload,
            )
        )

    def get_requests(self) -> List[Dict[str, Any]]:
        """Retrieve intercepted fetch requests."""
        data = self.driver.execute_script(
            "return window.__voiceTest ? window.__voiceTest.getRequests() : [];"
        )
        return data or []

    def clear_requests(self) -> None:
        """Clear recorded fetch requests."""
        self.driver.execute_script(
            "if (window.__voiceTest) { window.__voiceTest.clearRequests(); }"
        )

    def flags(self) -> Dict[str, Any]:
        """Inspect teardown flags for validation."""
        data = self.driver.execute_script(
            "return window.__voiceTest ? window.__voiceTest.getFlags() : {};"
        )
        return data or {}
