async function chargerLogs() {
    const service  = document.getElementById("service").value;
    const level    = document.getElementById("level").value;
    const fromDate = document.getElementById("from-date").value;
    const toDate   = document.getElementById("to-date").value;

    let url = "/logs/?";
    if (service)  url += `service=${service}&`;
    if (level)    url += `level=${level}&`;
    if (fromDate) url += `from_date=${fromDate}&`;
    if (toDate)   url += `to_date=${toDate}&`;

    const div = document.getElementById("liste-logs");
    div.innerHTML = "<p>Chargement...</p>";

    const res = await fetch(url);
    const logs = await res.json();
    div.innerHTML = "";

    if (!Array.isArray(logs) || logs.length === 0) {
        div.innerHTML = "<p>Aucun log trouvé.</p>";
        return;
    }

    div.innerHTML = logs.map(log => `
        <div class="log log-${log.level?.toLowerCase()}">
            <p><strong>${log.service}</strong> — <span class="level">${log.level}</span></p>
            <p>${log.message}</p>
            <p class="date">${new Date(log.created_at).toLocaleString("fr-FR")}</p>
        </div>
    `).join("");
}

async function chargerStats() {
    const div = document.getElementById("stats");
    div.innerHTML = "<p>Chargement...</p>";

    const res = await fetch("/logs/stats");
    const stats = await res.json();

    div.innerHTML = `
        <p><strong>Total :</strong> ${stats.total}</p>
        <h3>Par service</h3>
        ${Object.entries(stats.par_service).map(([k, v]) => `<p>${k} : ${v}</p>`).join("")}
        <h3>Par level</h3>
        ${Object.entries(stats.par_level).map(([k, v]) => `<p>${k} : ${v}</p>`).join("")}
    `;
}

function deconnexion() {
    localStorage.removeItem("token");
    window.location.href = "/login-agent-page";
}

document.addEventListener("DOMContentLoaded", () => {
    chargerLogs();
    chargerStats();
});