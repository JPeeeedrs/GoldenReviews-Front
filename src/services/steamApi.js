const BASE_URL = "http://localhost:8000";

export async function searchSteamGames(term) {
	const res = await fetch(`${BASE_URL}/search?q=${encodeURIComponent(term)}`);

	if (!res.ok) throw new Error("Erro ao buscar jogos");

	return await res.json();
}

export async function analyzeGame(gameName) {
	const res = await fetch(
		`${BASE_URL}/analyze/${encodeURIComponent(gameName)}`,
	);

	if (res.status === 202) {
		return { status: 202, data: await res.json() };
	}

	if (!res.ok) throw new Error("Erro ao analisar reviews");

	return { status: 200, data: await res.json() };
}
