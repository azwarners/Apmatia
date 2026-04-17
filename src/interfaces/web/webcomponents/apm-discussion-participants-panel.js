class ApmDiscussionParticipantsPanel extends HTMLElement {
  constructor() {
    super();
    this._participants = [];
  }

  connectedCallback() {
    if (this._participants.length === 0) {
      this._participants = [
        { id: "user", label: "You", role: "owner", isOnline: true },
        { id: "assistant", label: "Assistant", role: "system", isOnline: true },
      ];
    }
    this.render();
  }

  setParticipants(participants) {
    this._participants = Array.isArray(participants) ? participants : [];
    this.render();
  }

  getParticipants() {
    return this._participants.slice();
  }

  render() {
    const escapeHtml = (value) =>
      String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");

    const rows = this._participants
      .map((participant) => {
        const stateLabel = participant.isOnline ? "Online" : "Offline";
        const role = participant.role ? String(participant.role) : "member";
        const id = String(participant.id || participant.label || role);
        const label = String(participant.label || id);
        return `
          <button type="button" class="apm-participant-row" data-participant-id="${escapeHtml(id)}">
            <span class="apm-participant-main">${escapeHtml(label)}</span>
            <span class="apm-participant-meta">${escapeHtml(role)} · ${escapeHtml(stateLabel)}</span>
          </button>
        `;
      })
      .join("");

    this.innerHTML = `
      <section class="apm-panel apm-discussion-participants-panel" aria-label="Discussion participants">
        <header class="apm-panel-header">Participants</header>
        <div class="apm-panel-body">
          ${rows || '<div class="apm-panel-empty">No participants</div>'}
        </div>
        <div class="apm-panel-footer apm-participant-actions">
          <button type="button" class="secondary-action apm-participant-add-user">+ User</button>
          <button type="button" class="secondary-action apm-participant-add-agent">+ Agent</button>
          <button type="button" class="secondary-action apm-participant-add-model">+ Model</button>
        </div>
      </section>
    `;

    this.querySelectorAll(".apm-participant-row").forEach((rowEl) => {
      rowEl.addEventListener("click", () => {
        const participantId = rowEl.getAttribute("data-participant-id");
        this.dispatchEvent(
          new CustomEvent("apm-discussion-participant-select", {
            bubbles: true,
            detail: { participantId },
          })
        );
      });
    });
  }
}

if (!customElements.get("apm-discussion-participants-panel")) {
  customElements.define("apm-discussion-participants-panel", ApmDiscussionParticipantsPanel);
}
