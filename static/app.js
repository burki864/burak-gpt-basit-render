async function sendChat() {
    const username = document.getElementById("username").value;
    const prompt = document.getElementById("prompt").value;

    const res = await fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({username, prompt})
    });

    const data = await res.json();
    document.getElementById("chat").innerHTML +=
        `<p><b>Sen:</b> ${prompt}</p><p><b>BurakGPT:</b> ${data.reply}</p>`;
}

async function sendImage() {
    const username = document.getElementById("username").value;
    const prompt = document.getElementById("prompt").value;

    const res = await fetch("/image", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({username, prompt})
    });

    const data = await res.json();
    document.getElementById("chat").innerHTML +=
        `<img src="${data.image}" width="300">`;
}

