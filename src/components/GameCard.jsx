const getCapsule = (appid, fallback) =>
	fallback ||
	`https://cdn.cloudflare.steamstatic.com/steam/apps/${appid}/capsule_184x69.jpg`;

export default function GameCard({ game, onSelect, selected }) {
	const cover = getCapsule(game.appid, game.image);
	return (
		<div className='card'>
			<img src={cover} alt={game.name} loading='lazy' />

			<div className='info'>
				<strong>{game.name}</strong>
				<span>AppID: {game.appid}</span>
				{selected && <span className='selected'>Selecionado</span>}
			</div>

			<button onClick={() => onSelect(game)}>Selecionar</button>
		</div>
	);
}
