# static/js

## simli-client.esm.js

SDK oficial de Simli (`simli-client` 3.0.2 de npm) empaquetado como módulo ES.

### Por qué está acá y no se carga de un CDN

El paquete depende de `livekit-client` y **ningún CDN logra convertirlo** a
módulo ES. Probado el 09-ago-2026, todos fallan:

| CDN | Resultado |
|---|---|
| jsDelivr (`/+esm`) | `failed to resolve an internal import` |
| esm.run | mismo error |
| esm.sh | no devuelve el módulo |
| skypack | no devuelve el módulo |
| unpkg (archivo crudo) | `exports is not defined` — es CommonJS |

Servirlo desde acá además evita que la página dependa de que un CDN de
terceros esté disponible.

### Cómo regenerarlo

Cuando salga una versión nueva de `simli-client`:

```bash
mkdir simli_bundle && cd simli_bundle
npm init -y
npm install simli-client@<version> esbuild
echo "export { SimliClient, generateSimliSessionToken, generateIceServers, LogLevel } from 'simli-client';" > entrada.js
npx esbuild entrada.js --bundle --format=esm --minify --target=es2020 --outfile=../static/js/simli-client.esm.js
```

El bundle de la 3.0.2 pesa ~560 kb (lleva livekit-client adentro).

### API que usa la página

Verificada leyendo `dist/Client.d.ts` del paquete publicado:

```
new SimliClient(session_token, videoElement, audioElement, iceServers|null)
  .start()             -> Promise<void>
  .stop()              -> Promise<void>
  .sendAudioData(Uint8Array)
  .ClearBuffer()
  .on(evento, callback)
```
