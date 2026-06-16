import { useEffect, useState } from "react";
import SearchBox from "./components/SearchBox";
import Results from "./components/Results";
import SelectedGame from "./components/SelectedGame";
import ReviewAnalysis from "./components/ReviewAnalysis";
import RecommendedGames from "./components/RecommendedGames";

import { searchSteamGames, getReviews } from "./services/steamApi";

import "./styles/global.css";
import "./styles/analysis.css";

export default function App() {
	const [query, setQuery] = useState("");
	const [games, setGames] = useState([]);
	const [selected, setSelected] = useState(null);
	const [reviews, setReviews] = useState(null);
	const [maxReviews, setMaxReviews] = useState(1000);
	const [language, setLanguage] = useState("brazilian");
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState(null);

	const [showFoxy, setShowFoxy] = useState(false);

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

	function handleSelect(game) {
		setSelected(game);
		setReviews(null);
	}

	useEffect(() => {
		if (!loading || !selected) return;

		let active = true;

		const poll = async () => {
			try {
				const result = await getReviews(selected.appid, maxReviews, language);
				if (!active) return;

				if (result.status === 200) {
					setReviews({
						...result.data,
						meta: {
							language,
							maxReviewsRequested: maxReviews,
						},
					});
					setLoading(false);
				}
			} catch (e) {
				if (!active) return;
				console.error(e);
				setError("Não foi possível analisar as reviews agora.");
				setLoading(false);
			}
		};

		poll();
		const intervalId = setInterval(poll, 10000);
		return () => {
			active = false;
			clearInterval(intervalId);
		};
	}, [loading, selected, maxReviews, language]);

	function handleAnalyze() {
		if (!selected) return;
		const nomeDoJogo = selected.name.toLowerCase();

		if (
			nomeDoJogo.includes("death stranding 2") ||
			nomeDoJogo.includes("on the beach")
		) {
			const audioEasterEgg = new Audio(
				"../public/brksedu-impressionante-demais.mp3",
			);
			audioEasterEgg.volume = 0.25;

			audioEasterEgg
				.play()
				.catch((erro) => console.log("Erro ao tocar áudio:", erro));
		}
		if (
			nomeDoJogo.includes("fnaf 2") ||
			nomeDoJogo.includes("five nights at freddy's 2")
		) {
			const audioFnaf = new Audio("../public/foxy-scream-fnaf.mp3");
			audioFnaf.volume = 0.2;
			audioFnaf
				.play()
				.catch((erro) => console.log("Erro ao tocar áudio FNAF:", erro));

			setShowFoxy(true);

			setTimeout(() => {
				setShowFoxy(false);
			}, 5000);
		}

		setLoading(true);
		setReviews(null);
		setError(null);
	}

	return (
		<div className='container'>
			<h1>Golden Reviews</h1>
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

			{!query && !selected && <RecommendedGames onSelectGame={handleSelect} />}

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

			{!selected && query.length >= 2 && (
				<Results
					games={visibleGames}
					onSelect={handleSelect}
					selectedGame={selected}
				/>
			)}

			{selected && (
				<button
					className='analyze-btn'
					onClick={handleAnalyze}
					disabled={loading}
				>
					{loading
						? "Analisando com Golden Reviews..."
						: "Analisar com Golden Reviews"}
				</button>
			)}

			{error && <p className='error'>{error}</p>}
			{loading && (
				<div className='analysis-loading' role='status' aria-live='polite'>
					<div className='loading-wheel' aria-hidden='true'></div>
					<p>Processando reviews...</p>
				</div>
			)}

			<ReviewAnalysis data={reviews} />
			{showFoxy && (
				<img
					src='../public/fnaf-memes.gif'
					alt='Jumpscare do Foxy'
					className='jumpscare-overlay'
				/>
			)}
		</div>
	);
}
