const BASE_URL = "http://localhost:8000";

export async function searchSteamGames(term) {
	const res = await fetch(`${BASE_URL}/search?q=${encodeURIComponent(term)}`);

	if (!res.ok) throw new Error("Erro ao buscar jogos");

	return await res.json();
}

export async function getReviews(
	appid,
	maxReviews = 1000, // Padrão agora é 1000 
	language = "brazilian",
) {
	const params = new URLSearchParams({
		appid: appid,
		maxReviews: maxReviews,
		language: language,
	});

	const res = await fetch(`${BASE_URL}/reviews?${params.toString()}`);

	// Lógica de polling mantida da HEAD: 202 significa que a IA ainda está processando
	if (res.status === 202) {
		return { status: 202, data: await res.json() };
	}

	if (!res.ok) throw new Error("Erro ao analisar reviews");

	// 200 significa que o cache retornou o JSON completo
	return { status: 200, data: await res.json() };
}
