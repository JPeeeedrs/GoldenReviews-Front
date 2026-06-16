import { useEffect, useState } from "react";
import "../styles/recommended.css";

export default function RecommendedGames({ onSelectGame }) {
	const [recommended, setRecommended] = useState([]);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		async function fetchRecommended() {
			try {
				const response = await fetch("http://localhost:8000/recommended");
				if (response.ok) {
					const data = await response.json();
					setRecommended(data);
				}
			} catch (error) {
				console.error("Erro ao buscar jogos recomendados:", error);
			} finally {
				setLoading(false);
			}
		}
		fetchRecommended();
	}, []);

	if (loading || recommended.length === 0) return null;

	const carouselItems = [...recommended, ...recommended];

	return (
		<div className='recommended-section'>
			<h2 className='recommended-title'>Jogos Recomendados</h2>
			<div className='carousel-container'>
				<div className='carousel-track'>
					{carouselItems.map((game, index) => (
						<div
							key={`${game.appid}-${index}`}
							className='carousel-card'
							onClick={() => onSelectGame(game)}
							role='button'
							tabIndex={0}
						>
							<img src={game.image} alt={game.name} loading='lazy' />
							<div className='carousel-card-title'>{game.name}</div>
						</div>
					))}
				</div>
			</div>
		</div>
	);
}
