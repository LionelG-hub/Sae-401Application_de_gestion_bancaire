const params = new URLSearchParams(window.location.search);
const tokenUrl = params.get("token");
if (tokenUrl) localStorage.setItem("token", tokenUrl);
const token = localStorage.getItem("token");
if (!token) window.location.href = "http://localhost:8000/login-agent-page";
const headers = { "Authorization": `Bearer ${token}` };

async function chargerComptes() {
    const res = await fetch(`/agent/clients/${userId}/comptes`, { headers });
    const data = await res.json();
    const div = document.getElementById("liste-comptes");
    if (!Array.isArray(data) || data.length === 0) {
        div.innerHTML = "<p>Aucun compte trouvé.</p>";
        return;
    }
    div.innerHTML = data.map(c => `
        <div class="card-compte">
            <p><strong>Numéro :</strong> ${c.num_compte}</p>
            <p><strong>Solde :</strong> ${c.solde.toFixed(2)} €</p>
            <p><strong>Dernière opération :</strong> ${c.derniere_operation ? new Date(c.derniere_operation).toLocaleString("fr-FR") : "Aucune"}</p>
        </div>
    `).join("");
}

async function chargerOperations() {
    const res = await fetch(`/agent/clients/${userId}/operations`, { headers });
    const ops = await res.json();
    const div = document.getElementById("liste-operations");
    if (!Array.isArray(ops) || ops.length === 0) {
        div.innerHTML = "<p>Aucune opération.</p>";
        return;
    }
    const badge = { en_attente: 'attente', validee: 'validee', refusee: 'refusee' };
    div.innerHTML = ops.map(o => `
        <div class="card-operation">
            <p><strong>#${o.id}</strong> — ${o.type_op} — ${o.montant.toFixed(2)} €</p>
            <p>Source : ${o.compte_source ?? '—'} | Dest : ${o.compte_dest ?? '—'}</p>
            <p>Date : ${new Date(o.created_at).toLocaleString("fr-FR")}</p>
            <span class="badge badge-${badge[o.statut]}">${o.statut}</span>
        </div>
    `).join("");
}

function deconnexion() {
    localStorage.removeItem("token");
    window.location.href = "http://localhost:8000/login-agent-page";
}

document.addEventListener("DOMContentLoaded", () => {
    chargerComptes();
    chargerOperations();
});
