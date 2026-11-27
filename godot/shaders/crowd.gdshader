// Taraftarlar: tek MultiMesh, hareket + boyama + tribun maskesi GPU'da.
shader_type canvas_item;

uniform sampler2D tint_tex : filter_linear_mipmap;
uniform sampler2D mask_tex : filter_linear;
uniform vec2 mask_origin = vec2(0.0, 225.0);
uniform vec2 mask_size = vec2(1280.0, 237.0);
uniform vec2 atlas_px = vec2(1152.0, 1440.0);
uniform vec2 pitch = vec2(96.0, 144.0);
uniform vec2 inner = vec2(88.0, 136.0);
uniform float cols = 12.0;
uniform float t = 0.0;
uniform float excite = 0.15;
uniform float fill = 1.0;
uniform int sad = -1;
uniform vec4 shirts[6];   // [taraf*3 + ton]
uniform vec3 light = vec3(0.82, 0.82, 0.89);

varying vec2 wpos;
varying vec3 shirt;
varying vec3 team;

// Ornek verisi (instance transform shader'dan SONRA uygulanir, o yuzden konum burada):
// CUSTOM.x = dunya x, CUSTOM.y = dunya y, CUSTOM.z = hiz*100*8 + faz, CUSTOM.w = anahtar*8 + atkı*4 + hep*2 + esik
// COLOR.r = olcek, COLOR.g = dolma sirasi, COLOR.b = ton/2
void vertex() {
	vec2 pos = INSTANCE_CUSTOM.xy;
	float side = pos.x < 640.0 ? 0.0 : 1.0;
	float zz = INSTANCE_CUSTOM.z;
	float spd = floor(zz / 8.0) / 100.0;
	float ph = zz - floor(zz / 8.0) * 8.0;
	float w = INSTANCE_CUSTOM.w;
	float key = floor(w / 8.0);
	w -= key * 8.0;
	float scarf = step(4.0, w);
	w -= scarf * 4.0;
	float always = step(2.0, w);
	float thr = w - always * 2.0;
	float sc = COLOR.r;
	bool up = excite > thr;
	if (sad >= 0 && int(side) != sad) {
		up = false;
		always = 0.0;
	}
	bool act = up || always > 0.5;
	float b = abs(sin(t * spd * 0.45 + ph));
	float jump = act ? (0.5 + excite * 3.0) * b : 0.0;
	float pose = act ? (scarf > 0.5 ? 2.0 : 1.0) : 0.0;
	float cell = key * 3.0 + pose;
	vec2 cxy = vec2(mod(cell, cols), floor(cell / cols));
	UV = (cxy * pitch + (pitch - inner) * 0.5 + UV * inner) / atlas_px;
	int shade = int(round(COLOR.b * 2.0));
	shirt = shirts[int(side) * 3 + shade].rgb;
	team = shirts[int(side) * 3].rgb;
	vec2 size = vec2(22.0, 34.0) * sc;
	VERTEX.y -= jump / size.y;
	wpos = pos + VERTEX * size;
	if (COLOR.g > fill) {
		VERTEX = vec2(-99999.0);
	}
	COLOR = vec4(1.0);
}

void fragment() {
	vec4 base = texture(TEXTURE, UV);
	vec3 m = texture(tint_tex, UV).rgb;
	vec3 c = base.rgb;
	c = mix(c, c * shirt, m.r);
	c = mix(c, c * team, m.g);
	float ma = texture(mask_tex, (wpos - mask_origin) / mask_size).a;
	COLOR = vec4(c * light, base.a * ma);
}
