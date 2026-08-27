/*!
 * mrf.mjs — ESM wrapper around mrf.js (named exports for `import { parse } from …`).
 *
 *   import mrf, { parse, validate } from "./mrf.mjs";
 */
import api from "./mrf.js";

export const VERSION = api.VERSION;
export const parse = api.parse;
export const parseFile = api.parseFile;
export const tokenize = api.tokenize;
export const toJSON = api.toJSON;
export const typesOf = api.typesOf;
export const recordsOf = api.recordsOf;
export const validate = api.validate;
export const Document = api.Document;
export const Record = api.Record;
export const RecordRef = api.RecordRef;
export const InlineRecord = api.InlineRecord;
export const TypeDef = api.TypeDef;
export const NamedType = api.NamedType;
export const AnonType = api.AnonType;
export const FieldDef = api.FieldDef;
export const MRFSyntaxError = api.MRFSyntaxError;

export default api;
