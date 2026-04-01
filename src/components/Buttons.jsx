import "../styles/buttons.css";

export default function Buttons({ onClearSearch, onClearSelected }) {
	return (
		<div className='buttons'>
			<button onClick={onClearSearch}>Limpar busca</button>
			<button onClick={onClearSelected}>Limpar seleção</button>
		</div>
	);
}
