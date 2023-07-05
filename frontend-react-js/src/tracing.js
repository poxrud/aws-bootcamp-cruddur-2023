// tracing.js
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { WebTracerProvider, BatchSpanProcessor } from '@opentelemetry/sdk-trace-web';
import { ZoneContextManager } from '@opentelemetry/context-zone';
import { Resource } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';
import { registerInstrumentations } from '@opentelemetry/instrumentation';

import { XMLHttpRequestInstrumentation } from '@opentelemetry/instrumentation-xml-http-request';
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch';

// const { ConsoleSpanExporter, SimpleSpanProcessor } = require( '@opentelemetry/sdk-trace-base');

const exporter = new OTLPTraceExporter({
  url: 'https://api.honeycomb.io:443/v1/traces',
  headers: {
    "x-honeycomb-team": "5FazcfH76AKoMcbeWLfP3X",
    "x-honeycomb-dataset": "browser"
  }
});
const provider = new WebTracerProvider({
  resource: new Resource({
    [SemanticResourceAttributes.SERVICE_NAME]: 'browser',
  }),
});
// provider.addSpanProcessor(new SimpleSpanProcessor(new ConsoleSpanExporter()));
provider.addSpanProcessor(new BatchSpanProcessor(exporter));
provider.register({
  contextManager: new ZoneContextManager()
});

registerInstrumentations({
  instrumentations: [
    new XMLHttpRequestInstrumentation({
      propagateTraceHeaderCorsUrls: [
        /.+/g, //Regex to match your backend urls. This should be updated.
      ]
    }),
    new FetchInstrumentation({
      propagateTraceHeaderCorsUrls: [
        /.+/g, //Regex to match your backend urls. This should be updated.
      ]
    }),
  ],
});