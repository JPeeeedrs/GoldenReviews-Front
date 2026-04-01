import { useEffect, useState } from "react";
import SearchBox from "./components/SearchBox";
import Buttons from "./components/Buttons";
import Results from "./components/Results";
import SelectedGame from "./components/SelectedGame";
import ReviewAnalysis from "./components/ReviewAnalysis";

import { searchSteamGames, getReviews } from "./services/steamApi";

import "./styles/global.css";
import "./styles/analysis.css";

export default function App() {
	const [query, setQuery] = useState("");
	const [games, setGames] = useState([]);
	const [selected, setSelected] = useState(null);
	const [reviews, setReviews] = useState(null);
	const [maxReviews, setMaxReviews] = useState(1200);
	const [language, setLanguage] = useState("brazilian");
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState(null);

	// 🔎 Buscar jogos
	useEffect(() => {
		if (query.length < 2) {
			setGames([]);
			return;
		}

		const timeout = setTimeout(async () => {
			try {
				const data = await searchSteamGames(query);
				setGames(data);
			} catch (e) {
				console.error(e);
			}
		}, 400);

		return () => clearTimeout(timeout);
	}, [query]);

	// 🎮 Selecionar jogo (AGORA NÃO ANALISA)
	function handleSelect(game) {
		setSelected(game);
		setReviews(null);
	}

	// 📊 BOTÃO ANALISAR
	async function handleAnalyze() {
		if (!selected) return;

		setLoading(true);
		setReviews(null);
		setError(null);

		try {
			const data = await getReviews(selected.appid, maxReviews, language);
			setReviews(data);
		} catch (e) {
			console.error(e);
			setError("Não foi possível analisar as reviews agora.");
		}

		setLoading(false);
	}

	return (
		<div className='container'>
			<h1>🔎 Buscador de jogos da Steam</h1>
			<p>Digite o nome do jogo e veja sugestões em tempo real.</p>

			<SearchBox value={query} onChange={setQuery} />

			<Buttons
				onClearSearch={() => {
					setQuery("");
					setSelected(null);
					setReviews(null);
				}}
				onClearSelected={() => {
					setSelected(null);
					setReviews(null);
				}}
			/>

			{/* 🔢 quantidade */}
			<div className='limit-box'>
				<div>
					<label>Qtd. máxima de reviews</label>
					<input
						type='number'
						value={maxReviews}
						onChange={(e) => setMaxReviews(Number(e.target.value))}
						min={200}
						max={5000}
					/>
				</div>

				<div>
					<label>Idioma</label>
					<select
						value={language}
						onChange={(e) => setLanguage(e.target.value)}
					>
						<option value='brazilian'>Português (Brasil)</option>
						<option value='english'>Inglês</option>
						<option value='all'>Todos idiomas</option>
					</select>
				</div>
			</div>

			{!query && <div className='info'>Digite algo para começar.</div>}

			{/* 🔙 voltar */}
			{selected && (
				<button
					style={{ marginTop: "15px" }}
					onClick={() => {
						setSelected(null);
						setReviews(null);
					}}
				>
					🔙 Voltar
				</button>
			)}

			<SelectedGame game={selected} />

			{/* 📋 lista */}
			{!selected && (
				<Results
					games={games}
					onSelect={handleSelect}
					selectedGame={selected}
				/>
			)}

			{/* 🚀 BOTÃO ANALISAR */}
			{selected && (
				<button
					className='analyze-btn'
					onClick={handleAnalyze}
					disabled={loading}
				>
					{loading ? "Analisando..." : "📊 Analisar Reviews"}
				</button>
			)}

			{selected && (
				<p className='hint'>
					🤖 Validação semântica com IA chegará em breve para garantir
					consistência das reviews.
				</p>
			)}

			{/* ⏳ loading */}
			{error && <p className='error'>{error}</p>}
			{loading && <p>🔄 Processando reviews...</p>}

			{/* 📊 resultado */}
			<ReviewAnalysis data={reviews} />
		</div>
	);
}
