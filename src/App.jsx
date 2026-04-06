import { useEffect, useState } from "react";
import SearchBox from "./components/SearchBox";
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
		if (query.length < 2) return;

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

	const visibleGames = query.length < 2 ? [] : games;

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
			<h1>🏆 Golden Reviews</h1>
			<p>
				Analisador de reviews da Steam. Digite o nome do jogo e veja sugestões
				em tempo real.
			</p>

			<SearchBox
				value={query}
				onChange={setQuery}
				onClear={() => {
					setQuery("");
					setSelected(null);
					setReviews(null);
				}}
				showClear={Boolean(query) || Boolean(selected)}
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

			{!query && <div className='status-info'>Digite algo para começar.</div>}

			{/* 🔙 voltar */}
			{selected && (
				<button
					className='back-btn'
					onClick={() => {
						setSelected(null);
						setReviews(null);
					}}
				>
					<span aria-hidden='true'>↩</span>
					Voltar
				</button>
			)}

			<SelectedGame game={selected} />

			{/* 📋 lista */}
			{!selected && (
				<Results
					games={visibleGames}
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
					{loading
						? "Analisando com Golden Reviews..."
						: "📊 Analisar com Golden Reviews"}
				</button>
			)}

			{selected && (
				<p className='hint'>
					🤖 O Golden Reviews terá validação semântica com IA em breve para
					garantir consistência das reviews.
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
