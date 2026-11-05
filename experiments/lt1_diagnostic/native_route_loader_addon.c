/* Fixed ordinary-tooling target. No LT1, I/O, callbacks or external inputs. */
#include <node_api.h>

NAPI_MODULE_INIT() {
  napi_value marker;
  if (napi_create_int32(env, 51020, &marker) != napi_ok ||
      napi_set_named_property(env, exports, "marker", marker) != napi_ok) {
    return NULL;
  }
  return exports;
}
