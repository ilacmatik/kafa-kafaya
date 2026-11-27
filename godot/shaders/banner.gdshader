// Gemini'nin beyaz pankart/bayraklarini forma rengine boyar (golgeler korunur).
// Boya rengi draw_texture_rect'in modulate rengi (COLOR) olarak gelir.
shader_type canvas_item;

void fragment() {
	vec4 tex = texture(TEXTURE, UV);
	float mn = min(tex.r, min(tex.g, tex.b));
	float mx = max(tex.r, max(tex.g, tex.b));
	float cloth = smoothstep(0.55, 0.62, mn) * (1.0 - smoothstep(0.13, 0.19, mx - mn));
	float lum = (tex.r + tex.g + tex.b) / 3.0;
	vec3 c = mix(tex.rgb, COLOR.rgb * (0.25 + 0.8 * lum), cloth);
	COLOR = vec4(c, tex.a * COLOR.a);
}
