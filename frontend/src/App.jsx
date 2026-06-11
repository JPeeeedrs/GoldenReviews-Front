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
	const [maxReviews, setMaxReviews] = useState(1000); //Padrão é 1000! 
	const [language, setLanguage] = useState("brazilian");
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState(null);

	// Buscar jogos
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

	// Polling Effect - Mantido da HEAD com as novas chamadas do ABSA
	useEffect(() => {
		if (!loading || !selected) return;

		let active = true;

		const poll = async () => {
			try {
				const result = await getReviews(selected.appid, maxReviews, language);
				if (!active) return;

				// Se o cache já concluiu e montou o JSON completo (Status 200)
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
				// Se retornar 202, continua em polling silenciosamente
			} catch (e) {
				if (!active) return;
				console.error(e);
				setError("Não foi possível analisar as reviews agora.");
				setLoading(false);
			}
		};

		poll();
		const intervalId = setInterval(poll, 10000); //FIX : aumento de 2000(2s) para 10000(10s)
		return () => {
			active = false;
			clearInterval(intervalId);
		};
	}, [loading, selected, maxReviews, language]);

	// BOTÃO ANALISAR
	function handleAnalyze() {
		if (!selected) return;

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

			<div className='limit-box' style={{ justifyContent: 'center' }}>
			{/* Remoção da opção do usuário definir quantidade máxima no FRONT. */}
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

			{!selected && (
				<Results
					games={visibleGames}
					onSelect={handleSelect}
					selectedGame={selected}
				/>
			)}

			{/* Botão de Análise atualizado com a nova UX */}
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
		</div>
	);
}
