
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

function deconnexion() {
    localStorage.removeItem("token");
    window.location.href = "/login-agent-page";
}

document.addEventListener("DOMContentLoaded", chargerComptes);

