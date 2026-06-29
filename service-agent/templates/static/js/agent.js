
const params = new URLSearchParams(window.location.search);
const tokenUrl = params.get("token");
if (tokenUrl) localStorage.setItem("token", tokenUrl);

const token = localStorage.getItem("token");
if (!token) window.location.href = "http://localhost:8000/login-agent-page";

const headers = { "Authorization": `Bearer ${token}` };


async function chargerOperations() {
    const res = await fetch("/agent/operations/en-attente", { headers });
    const ops = await res.json();
    const div = document.getElementById("liste-operations");

    if (!Array.isArray(ops) || ops.length === 0) {
        div.innerHTML = "<p>Aucune opération en attente.</p>";
        return;
    }

    div.innerHTML = ops.map(op => `
        <div class="card-operation">
            <p><strong>#${op.id}</strong> — ${op.type_op} — ${op.montant.toFixed(2)} €</p>
            <p>Compte source : ${op.compte_source ?? "—"} | Dest : ${op.compte_dest ?? "—"}</p>
            <p>Date : ${new Date(op.created_at).toLocaleString("fr-FR")}</p>
            <button onclick="validerOperation(${op.id})">✓ Valider</button>
            <button onclick="refuserOperation(${op.id})">✗ Refuser</button>
        </div>
    `).join("");
}

async function validerOperation(id) {
    const res = await fetch(`/agent/operations/${id}/valider`, { method: "PATCH", headers });
    alert(res.ok ? `Opération #${id} validée.` : "Erreur lors de la validation.");
    if (res.ok) chargerOperations();
}

async function refuserOperation(id) {
    const res = await fetch(`/agent/operations/${id}/refuser`, { method: "PATCH", headers });
    alert(res.ok ? `Opération #${id} refusée.` : "Erreur lors du refus.");
    if (res.ok) chargerOperations();
}

async function rechercherComptes() {
    const userId = document.getElementById("user-id").value.trim();
    if (!userId) { alert("Veuillez entrer un ID client."); return; }
    console.log("token:", token);
    console.log("headers:", headers);
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

function deconnexion() {
    localStorage.removeItem("token");
    window.location.href = 'http://localhost:8000/login-agent-page';
}

document.addEventListener("DOMContentLoaded", chargerOperations);

