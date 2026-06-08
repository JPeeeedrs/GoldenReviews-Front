import GameCard from "./GameCard";
import "../styles/cards.css";

export default function Results({ games, onSelect, selectedGame }) {
	if (!games.length) return <p>Nenhum resultado encontrado.</p>;

	return (
		<div className='results'>
			{games.map((game) => (
				<GameCard
					key={game.appid}
					game={game}
					onSelect={onSelect}
					selected={selectedGame?.appid === game.appid}
				/>
			))}
		</div>
	);
}
