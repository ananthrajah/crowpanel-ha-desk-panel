#pragma once
// desk_layout.h — v1.0.0 (2026-10-17). Used by crowpanel-desk.yaml >= 3.0.0.
// Paints the 4 desktop-app-controlled pages (12 buttons each) from the compact
// strings published by HA's sensor.desk_panel_layout:
//   pN_labels   "Mancave 1\nGuest Room\n..."      (one line per slot)
//   pN_entities "light.x\nswitch.y\n..."
//   pN_states   "10x1..."  '1' on, '0' off, 'x' unavailable/missing  (one char per slot)

#include <string>
#include <vector>

namespace desk_layout {

inline std::vector<std::string> split_lines(const std::string &s) {
  std::vector<std::string> out;
  size_t start = 0;
  while (start <= s.size()) {
    size_t nl = s.find('\n', start);
    if (nl == std::string::npos) nl = s.size();
    out.emplace_back(s.substr(start, nl - start));
    start = nl + 1;
  }
  return out;
}

inline std::string entity_at(const std::string &entities, int i) {
  auto v = split_lines(entities);
  return (i >= 0 && i < (int) v.size()) ? v[i] : std::string();
}

inline const char *icon_for(const std::string &entity) {
  auto dom = entity.substr(0, entity.find('.'));
  if (dom == "light") return "";
  if (dom == "scene" || dom == "script") return "";
  if (dom == "media_player") return "";
  if (dom == "climate" || dom == "fan") return "";
  if (dom == "cover") return "";
  return "";
}

// Show/hide each slot and set its "icon + label" text.
inline void apply_labels(lv_obj_t *const *btns, lv_obj_t *const *lbls, int n,
                         const std::string &labels, const std::string &entities) {
  auto names = split_lines(labels);
  auto ents = split_lines(entities);
  for (int i = 0; i < n; i++) {
    std::string ent = i < (int) ents.size() ? ents[i] : "";
    std::string name = i < (int) names.size() ? names[i] : "";
    if (ent.empty()) {
      lv_obj_add_flag(btns[i], LV_OBJ_FLAG_HIDDEN);
      continue;
    }
    std::string text = std::string(icon_for(ent)) + "\n" + (name.empty() ? ent : name);
    lv_label_set_text(lbls[i], text.c_str());
    lv_obj_remove_flag(btns[i], LV_OBJ_FLAG_HIDDEN);
  }
}

// Green = on, black = off, dimmed = unavailable / not found in HA.
inline void apply_states(lv_obj_t *const *btns, int n, const std::string &states) {
  for (int i = 0; i < n; i++) {
    char c = i < (int) states.size() ? states[i] : '0';
    if (c == '1')
      lv_obj_add_state(btns[i], LV_STATE_CHECKED);
    else
      lv_obj_remove_state(btns[i], LV_STATE_CHECKED);
    lv_obj_set_style_opa(btns[i], c == 'x' ? LV_OPA_40 : LV_OPA_COVER, LV_PART_MAIN);
  }
}

}  // namespace desk_layout
