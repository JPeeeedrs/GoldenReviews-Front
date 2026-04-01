export async function searchSteamGames(term) {
	const res = await fetch(
		`http://localhost:5000/search?q=${encodeURIComponent(term)}`,
	);

	if (!res.ok) throw new Error("Erro ao buscar jogos");

	return await res.json();
}

// 📊 REVIEWS
export async function getReviews(appid, maxReviews, language = "brazilian") {
	const params = new URLSearchParams({
		appid,
		maxReviews,
		language,
	});

	const res = await fetch(`http://localhost:5000/reviews?${params.toString()}`);

	if (!res.ok) throw new Error("Erro ao buscar reviews");

	return await res.json();
}
