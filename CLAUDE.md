# Giocapensa

(Repository `giocapensa`, pubblicato con GitHub Pages all'indirizzo `…github.io/giocapensa/`. Non rinominarlo: cambierebbe l'indirizzo e l'icona già aggiunta alla Home dei telefoni smetterebbe di funzionare. Tutti i percorsi nelle pagine sono relativi, quindi il nome del repository non compare nel codice.)

Sei giochi touch per un bambino di circa tre anni, pubblicati con GitHub Pages dalla radice del ramo `main` e usati come app sulla schermata Home di un iPhone. Niente server, niente dipendenze: HTML, CSS, SVG e JavaScript scritti a mano.

## Come si lavora

- Le pagine nella radice (`index.html`, `via-libera.html`, `palline.html`, `labirinti.html`, `acqua.html`, `incastri.html`, `adesivi.html`, `sw.js`, `manifest.json`) sono **generate**. Non modificarle a mano: si modifica `src/` e poi si esegue
  `python3 src/build.py`
- Prima di ogni commit: `node src/tests/verify.js` deve finire con «Tutti i livelli verificati». Controlla che ogni livello sia risolvibile e che il minimo salvato sia quello vero.
- `build.py` dà alla cache offline un nome che dipende dal contenuto delle pagine: ogni modifica arriva da sola ai telefoni, non c'è nessuna versione da aggiornare a mano.
- Dopo il merge su `main` GitHub Pages pubblica in pochi minuti.

## Struttura

| Cartella | Contenuto |
| --- | --- |
| `src/shared/` | `kit.html` e `kit.js`: intestazione, contatori, pulsanti Annulla / Ricomincia / Aiuto, elenco livelli, pannello di vittoria, suoni, coriandoli, salvataggio. Li usano Labirinti, Acqua ai fiori e Incastri. |
| `src/labirinti/`, `src/acqua/`, `src/incastri/` | `logic.js` (regole e risolutore, senza DOM), `game.js` (scena SVG e gesti), `game.css`, `levels.json`, e il generatore dei livelli (`gen.py` o `gen.cpp`). |
| `src/palline/` | Palline nei tubi: pagina completa (`head_body.html`), `logic.js`, `main.js`, `levels.json`, generatore `gen.cpp` + `pick.py`. |
| `src/via-libera/` | Via libera (tipo Rush Hour): `head.html`, `body.html`, `logic.js`, `main.js`, `levels.json`, generatore `gen.cpp`. Ha cinque stili grafici e partite con nome. |
| `src/adesivi/` | Adesivi e numeri: una sola pagina autonoma. In alto una tessera per ogni adesivo richiesto, con il numero grande e il disegno (prima un solo tipo da 1 a 10, poi due e tre tipi insieme con numeri fino a 5 e 4); il bambino attacca quegli adesivi, in quel numero, e preme il tasto verde; il gioco conta ad alta voce, tipo per tipo, solo gli adesivi richiesti (gli altri non contano e possono restare); un tipo contato giusto è chiuso: tessera verde con spunta, adesivo spento nel cassetto, quelli già messi non si spostano più; un tipo sbagliato si corregge e si riconferma; chiusi tutti i tipi si passa al livello successivo (sintesi vocale del dispositivo, `it-IT`) e, se il numero è giusto, blocca la scena e mostra la vittoria. Dopo un errore compaiono i pallini sotto il numero. Il tasto «123» passa al gioco libero. Gli adesivi che «stanno in piedi» (animali, razzo, trenino, pianta…) si agganciano al mobile vicino a cui vengono lasciati (letto, comodino, mensola, davanzale: tabella `SURF`), non finiscono mai uno esattamente sopra l'altro, e con un tocco sulla tessera trovano da soli un posto libero. Il cassetto si sfoglia con due frecce, non col dito. Tessere e schede inquadrano il disegno reale di ogni adesivo (tabella `FIT`, misurata con `getBBox()` escludendo gli aloni `.glow`, più 5 unità di margine): aggiungendo o ridisegnando un adesivo va aggiornata anche quella riga, altrimenti il disegno risulta fuori centro o tagliato. |
| `src/home/` | La schermata iniziale con i sei riquadri. |

In Incastri le sagome sono disegnate a mano in `src/incastri/gen.py` (tabella `FORME`, in ASCII: razzo, gatto, castello, dinosauro…) e tagliate dal programma in pezzi da 3 a 6 caselle, con poche soluzioni possibili; il nome della sagoma sta nel livello (`n`) e la tabella `NOMI` in `game.js` lo trasforma in «Riempi il razzo» e «Razzo finito!». Per aggiungere una sagoma: una voce in `FORME`, una in `NOMI`, poi `python3 src/incastri/gen.py > src/incastri/levels.json`.
| `src/pwa/` | Icone e modello del service worker. |

Un gioco nuovo basato su `src/shared` fornisce a `Kit.start({...})`: `key`, `count`, `minOf(i)`, `load(i)`, `moves()`, `canUndo()`, `undo()`, `hint()`, `clearHint()`, più i testi. Va poi aggiunto a `build.py` e a `src/home/home.html`.

## Regole di progetto (decise con il genitore, non cambiarle senza chiedere)

- **Chi gioca non sa leggere.** Tutto deve capirsi da figure, animazioni e suoni. I testi sono per l'adulto.
- **Niente tempo, vite, sconfitte, premi da collezionare o serie giornaliere.** Annulla sempre disponibile, tutti i livelli aperti.
- **I giochi sono di logica**, sul modello di Via libera: ogni livello ha un minimo di mosse vero, calcolato da un risolutore, e i livelli sono generati e verificati, mai disegnati a mano.
- **L'aiuto va guadagnato:** si sblocca dopo 40 secondi sul livello o 8 mosse, e dopo ogni uso l'attesa riparte (30 secondi o 6 mosse). Un anello attorno al pulsante mostra quanto manca. Il tempo scorre solo con il gioco in primo piano.
- **Stile grafico «Pastello»:** colori piatti o sfumature morbide, contorno spesso color prugna `#4A3B52`, forme tonde, faccine con guance rosa, molte animazioni (parti che si muovono da sole, reazioni al tocco, scintille, coriandoli). Rispettare `prefers-reduced-motion`.
- **Colori e soggetti:** rosso, arancione, giallo, blu, verde e turchese decisi; niente rosa o lilla dominanti, cuori, fiorellini e farfalle come decorazione principale. Soggetti graditi: veicoli, razzi, aerei, trenini, dinosauri, palloni, animali.
- **Niente personaggi o grafiche protette** (Super Mario, Peppa Pig e simili): solo disegni originali.
- **Niente zoom per sbaglio:** su iPhone due tocchi rapidi ingrandiscono la pagina e tagliano fuori l'interfaccia. `src/shared/tocco.js` blocca il secondo tocco rapido e il pizzico solo dentro le aree di gioco (`.stage`, `.scene`, `.tray`, `.traywrap`, `.board`), che funzionano a eventi pointer; fuori di lì tutto resta normale. WebKit ignora `touch-action` sugli elementi SVG, quindi la regola va messa anche sul contenitore HTML `.stage`.
- **Bersagli grandi e gesti tolleranti:** trascinamenti che agganciano anche se imprecisi, un secondo dito ignorato, nessuno zoom o scorrimento accidentale (`touch-action`).
- **Impostazioni comuni** in `src/shared/opzioni.js` (`OPZ.get/set`, chiave `giocapensa.opzioni`): effetti sonori, musica, voce, lingua della voce (`it`/`en`), attesa dell'aiuto (`subito`/`attesa`/`mai`). Le legge ogni pagina: `sound.js` tace se gli effetti sono spenti, `music.js` segue `musica`, il cancelletto dell'aiuto in `kit.js`, in `palline/main.js` e in `via-libera/main.js` segue `aiuto`, la voce di Adesivi segue `voce` e `lingua`. Il pannello sta nella schermata iniziale (tasto ingranaggio) e comprende la cancellazione dei progressi, che non tocca le impostazioni. Un gioco nuovo non deve reintrodurre interruttori propri.
- **La schermata iniziale ha una musichetta** (`src/shared/music.js`): quattro accordi in do maggiore, melodia di marimba, tappeto e basso, loop di 20 secondi, con tasto per spegnerla (`giocapensa.musica` in localStorage). I browser non lasciano partire l'audio senza un tocco, quindi parte al primo tocco sulla pagina che non sia un riquadro di gioco, e si ferma quando la pagina viene lasciata o nascosta. I giochi non hanno musica, solo effetti.
- **Suoni sintetizzati con Web Audio**, senza file audio, dal motore comune `src/shared/sound.js` (`SFX.play(nome, {i | note})`: strumenti marimba, campanella, pop, tonfo, fruscio, boing, bollicine, accordi; compressore e riverbero). I suoni positivi stanno su una scala pentatonica, così le azioni in fila fanno una melodia; l'errore è un «boing» morbido, mai un ronzio. Via libera ha in più i suoi suoni per stile grafico. Su iPhone seguono la modalità silenzioso.
- **I progressi stanno in `localStorage`** (chiavi `via-libera.v2`, `palline.v1`, `labirinti.v1`, `acqua.v2`, `incastri.v1`, `adesivi.cameretta.v2`, `adesivi.numeri.v1`): non rinominarle, o i progressi si perdono.
- Il repository è pubblico: nessun nome o dato personale nelle pagine o nei commit.

## Cosa manca (idee già discusse)

- Adesivi ha una sola scena, la cameretta: mancano giardino, fattoria e spiaggia.
- Un settimo gioco possibile, «Guida tu»: mettere in fila delle frecce e poi far partire l'auto.
