const getCapsule = (appid, fallback) =>
	fallback ||
	`https://cdn.cloudflare.steamstatic.com/steam/apps/${appid}/header.jpg`;

export default function SelectedGame({ game }) {
	if (!game) return null;
	const cover = getCapsule(game.appid, game.image);

	return (
		<div className='selected-game'>
			<img src={cover} alt={game.name} />

			<div>
				<h3>{game.name}</h3>
				<p>AppID: {game.appid}</p>
			</div>
		</div>
	);
}
