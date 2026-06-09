import "../styles/gamehero.css";
import "../styles/global.css";

const numberFormat = (value) =>
	new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(value);

export default function GameHero({ game, summary, meta, aiNota }) {
	const avgHours = summary?.avg_hours;

	return (
		<header className='analysis-hero'>
			<div>
				<p className='eyebrow'>GOLDEN REVIEWS • JOGO EM ANÁLISE</p>
				<h2>{game?.name ?? ""}</h2>
				<div className='meta-line'>
					{(aiNota ?? summary?.overall_score) !== undefined && (
						<span>
							⭐ {numberFormat(aiNota ?? summary.overall_score)} Score Geral
							(IA)
						</span>
					)}
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
				<img src={game.header_image} alt={game?.name} className='game-cover' />
			)}
		</header>
	);
}
