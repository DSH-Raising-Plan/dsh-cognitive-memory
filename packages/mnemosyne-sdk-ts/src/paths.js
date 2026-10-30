/** Frozen Foundation REST paths — keep in sync with mnemosyne-sdk (Python). */
export const FOUNDATION_PATHS = {
  health: ["GET", "/api/v1/health"],
  discovery: ["GET", "/api/v1/discovery"],
  observe: ["POST", "/api/v1/observations"],
  retrieve: ["POST", "/api/v1/retrieve"],
  search: ["POST", "/api/v1/memories/search"],
  validate: ["POST", "/api/v1/udm/validate"],
  register: ["POST", "/api/v1/components/register"],
  pcip_request: ["POST", "/api/v1/pcip/exchange/request"],
  pcip_accept: ["POST", "/api/v1/pcip/exchange/accept"],
};
