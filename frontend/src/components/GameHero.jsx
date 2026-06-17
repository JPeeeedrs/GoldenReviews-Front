import "../styles/gamehero.css";
import "../styles/global.css";

const numberFormat = (value) =>
	new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(value);

export default function GameHero({ game, summary, meta }) {
	const avgHours = summary?.avg_hours;

	const positivePct =
		summary?.sentences_positive_percentage ?? summary?.positive_percentage ?? 0;
	const negativePct =
		summary?.sentences_negative_percentage ?? summary?.negative_percentage ?? 0;

	return (
		<header className='analysis-hero'>
			<div className='hero-main-row'>
				<div className='hero-text-content'>
					<h2>{game?.name ?? ""}</h2>

					<div className='meta-line'>
						{avgHours !== undefined && avgHours !== null && (
							<span>⏱️ {numberFormat(avgHours)} h médias jogadas</span>
						)}
						{game?.release_date && <span>📅 {game.release_date}</span>}
						{game?.price && <span>💰 {game.price}</span>}
					</div>

					{game?.short_description && (
						<p className='description'>{game.short_description}</p>
					)}
				</div>

				{game?.header_image && (
					<img
						src={game.header_image}
						alt={game?.name}
						className='game-cover'
					/>
				)}
			</div>

			{(positivePct > 0 || negativePct > 0) && (
				<div
					className='hero-sentiment-bar'
					title={`Frases: ${positivePct}% Positivas / ${negativePct}% Negativas`}
				>
					<div className='bar-green' style={{ width: `${positivePct}%` }}>
						{positivePct > 10 && <span>{positivePct}%</span>}
					</div>
					<div className='bar-red' style={{ width: `${negativePct}%` }}>
						{negativePct > 10 && <span>{negativePct}%</span>}
					</div>
				</div>
			)}
		</header>
	);
}
