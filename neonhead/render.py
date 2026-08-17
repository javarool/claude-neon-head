"""Render pipeline.

    1. afterglow    previous emissive frame * decay  -> ping-pong HDR target
    2. emissive     ribbons + glow dots, additive, into that target
    3. bloom        threshold -> 3 downsampled blurs
    4. tonemap      trail + weighted bloom -> screen, with sub-pixel jitter
    5. solids       eye whites, pupils, teeth painted on top, never bloomed

Step 5 is deliberate: the only non-glowing objects in the scene read as
physical things sitting inside the light.
"""

from __future__ import annotations

import numpy as np
import moderngl

RIBBON_VS = """
#version 330
in vec2 in_pos; in float in_side; in float in_arc; in float in_bright; in vec3 in_col;
uniform vec2 u_res;
out float v_side; out float v_arc; out float v_bright; out vec3 v_col;
void main() {
    v_side = in_side; v_arc = in_arc; v_bright = in_bright; v_col = in_col;
    vec2 p = in_pos / u_res * 2.0 - 1.0;
    gl_Position = vec4(p.x, -p.y, 0.0, 1.0);
}
"""

RIBBON_FS = """
#version 330
in float v_side; in float v_arc; in float v_bright; in vec3 v_col;
uniform vec3 u_core; uniform float u_time; uniform float u_hum; uniform float u_noise;
out vec4 f_col;
void main() {
    float d = abs(v_side);
    float core = pow(max(0.0, 1.0 - d * 4.2), 8.0);
    float halo = pow(max(0.0, 1.0 - d), 2.6);
    float hot   = 1.0 - u_noise + u_noise * (0.5 + 0.5 * sin(v_arc * 37.0 + u_time * 1.3));
    float mains = 1.0 - u_hum + u_hum * (0.5 + 0.5 * sin(u_time * 314.0));
    vec3 c = u_core * core * 0.85 + v_col * halo * 0.75;
    f_col = vec4(c * v_bright * hot * mains, 1.0);
}
"""

DOT_VS = """
#version 330
in vec2 in_quad;
in vec2 in_centre; in float in_radius; in float in_bright; in vec3 in_col;
uniform vec2 u_res;
out vec2 v_uv; out float v_bright; out vec3 v_col;
void main() {
    v_uv = in_quad; v_bright = in_bright; v_col = in_col;
    vec2 p = (in_centre + in_quad * in_radius) / u_res * 2.0 - 1.0;
    gl_Position = vec4(p.x, -p.y, 0.0, 1.0);
}
"""

DOT_FS = """
#version 330
in vec2 v_uv; in float v_bright; in vec3 v_col;
uniform vec3 u_core;
out vec4 f_col;
void main() {
    float d = length(v_uv);
    if (d > 1.0) discard;
    float core = pow(max(0.0, 1.0 - d * 2.2), 6.0);
    float halo = pow(max(0.0, 1.0 - d), 2.6);
    f_col = vec4((u_core * core + v_col * halo * 0.6) * v_bright, 1.0);
}
"""

SOLID_VS = """
#version 330
in vec2 in_pos; in vec4 in_col;
uniform vec2 u_res;
out vec4 v_col;
void main() {
    v_col = in_col;
    vec2 p = in_pos / u_res * 2.0 - 1.0;
    gl_Position = vec4(p.x, -p.y, 0.0, 1.0);
}
"""

SOLID_FS = """
#version 330
in vec4 v_col; out vec4 f_col;
void main() { f_col = v_col; }
"""

QUAD_VS = """
#version 330
in vec2 in_quad; out vec2 v_uv;
void main() { v_uv = in_quad * 0.5 + 0.5; gl_Position = vec4(in_quad, 0.0, 1.0); }
"""

DECAY_FS = """
#version 330
in vec2 v_uv; uniform sampler2D u_tex; uniform float u_decay;
out vec4 f_col;
void main() { f_col = vec4(texture(u_tex, v_uv).rgb * u_decay, 1.0); }
"""

THRESH_FS = """
#version 330
in vec2 v_uv; uniform sampler2D u_tex; uniform float u_thr; uniform float u_knee;
out vec4 f_col;
void main() {
    vec3 c = texture(u_tex, v_uv).rgb;
    float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
    f_col = vec4(c * smoothstep(u_thr, u_thr + u_knee, l), 1.0);
}
"""

COPY_FS = """
#version 330
in vec2 v_uv; uniform sampler2D u_tex; out vec4 f_col;
void main() { f_col = vec4(texture(u_tex, v_uv).rgb, 1.0); }
"""

BLUR_FS = """
#version 330
in vec2 v_uv; uniform sampler2D u_tex; uniform vec2 u_dir; out vec4 f_col;
void main() {
    vec3 s = texture(u_tex, v_uv).rgb * 0.2270270;
    s += (texture(u_tex, v_uv + u_dir * 1.3846).rgb
        + texture(u_tex, v_uv - u_dir * 1.3846).rgb) * 0.3162162;
    s += (texture(u_tex, v_uv + u_dir * 3.2307).rgb
        + texture(u_tex, v_uv - u_dir * 3.2307).rgb) * 0.0702702;
    f_col = vec4(s, 1.0);
}
"""

TONEMAP_FS = """
#version 330
in vec2 v_uv;
uniform sampler2D u_scene; uniform sampler2D u_b0; uniform sampler2D u_b1; uniform sampler2D u_b2;
uniform vec3 u_w; uniform vec3 u_bg;
uniform float u_exposure; uniform float u_gamma; uniform vec2 u_jitter;
out vec4 f_col;
void main() {
    vec2 uv = v_uv + u_jitter;
    vec3 c = texture(u_scene, uv).rgb;
    c += texture(u_b0, uv).rgb * u_w.x;
    c += texture(u_b1, uv).rgb * u_w.y;
    c += texture(u_b2, uv).rgb * u_w.z;
    c = vec3(1.0) - exp(-c * u_exposure);
    c = pow(c, vec3(1.0 / u_gamma));
    f_col = vec4(max(c, u_bg), 1.0);
}
"""


class Renderer:
    def __init__(self, ctx: moderngl.Context, cfg):
        self.ctx = ctx
        self.cfg = cfg
        quad = np.array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1], np.float32)
        self.quad_vbo = ctx.buffer(quad.tobytes())

        self.prog_ribbon = ctx.program(vertex_shader=RIBBON_VS, fragment_shader=RIBBON_FS)
        self.prog_dot = ctx.program(vertex_shader=DOT_VS, fragment_shader=DOT_FS)
        self.prog_solid = ctx.program(vertex_shader=SOLID_VS, fragment_shader=SOLID_FS)
        self.prog_decay = ctx.program(vertex_shader=QUAD_VS, fragment_shader=DECAY_FS)
        self.prog_thresh = ctx.program(vertex_shader=QUAD_VS, fragment_shader=THRESH_FS)
        self.prog_copy = ctx.program(vertex_shader=QUAD_VS, fragment_shader=COPY_FS)
        self.prog_blur = ctx.program(vertex_shader=QUAD_VS, fragment_shader=BLUR_FS)
        self.prog_tone = ctx.program(vertex_shader=QUAD_VS, fragment_shader=TONEMAP_FS)

        self.vao_decay = self._quad_vao(self.prog_decay)
        self.vao_thresh = self._quad_vao(self.prog_thresh)
        self.vao_copy = self._quad_vao(self.prog_copy)
        self.vao_blur = self._quad_vao(self.prog_blur)
        self.vao_tone = self._quad_vao(self.prog_tone)

        self.vbo_ribbon = ctx.buffer(reserve=1 << 21, dynamic=True)
        self.vao_ribbon = ctx.vertex_array(
            self.prog_ribbon,
            [(self.vbo_ribbon, "2f 1f 1f 1f 3f",
              "in_pos", "in_side", "in_arc", "in_bright", "in_col")])

        self.vbo_dot = ctx.buffer(reserve=1 << 17, dynamic=True)
        self.vao_dot = ctx.vertex_array(
            self.prog_dot,
            [(self.quad_vbo, "2f", "in_quad"),
             (self.vbo_dot, "2f 1f 1f 3f/i",
              "in_centre", "in_radius", "in_bright", "in_col")])

        self.vbo_solid = ctx.buffer(reserve=1 << 20, dynamic=True)
        self.vao_solid = ctx.vertex_array(
            self.prog_solid, [(self.vbo_solid, "2f 4f", "in_pos", "in_col")])

        self.size = (0, 0)
        self._targets = []

    def _quad_vao(self, prog):
        return self.ctx.vertex_array(prog, [(self.quad_vbo, "2f", "in_quad")])

    # ---------------------------------------------------------------- FBOs

    def resize(self, w: int, h: int):
        w, h = max(8, w), max(8, h)
        if (w, h) == self.size:
            return
        for t in self._targets:
            t.release()
        self._targets = []
        mk = self._make
        self.trail_a, self.fb_trail_a = mk(w, h)
        self.trail_b, self.fb_trail_b = mk(w, h)
        self.bloom = []
        self.bloom_tmp = []
        for i in range(3):
            bw, bh = max(4, w >> (i + 1)), max(4, h >> (i + 1))
            t, fb = mk(bw, bh)
            t2, fb2 = mk(bw, bh)
            self.bloom.append((t, fb))
            self.bloom_tmp.append((t2, fb2))
        self.size = (w, h)
        self.fb_trail_a.clear(0, 0, 0, 1)
        self.fb_trail_b.clear(0, 0, 0, 1)

    def _make(self, w, h):
        tex = self.ctx.texture((w, h), 4, dtype="f2")
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        tex.repeat_x = tex.repeat_y = False
        fb = self.ctx.framebuffer(color_attachments=[tex])
        self._targets.extend([tex, fb])
        return tex, fb

    # ---------------------------------------------------------------- draw

    def draw(self, frame, t: float, screen_fb):
        ctx = self.ctx
        w, h = self.size
        post = self.cfg["post"]
        rib, dots, solid = frame.arrays()

        # 1. afterglow --------------------------------------------------
        self.fb_trail_b.use()
        ctx.disable(moderngl.BLEND)
        self.trail_a.use(0)
        self.prog_decay["u_tex"] = 0
        self.prog_decay["u_decay"] = float(post["afterglow"])
        self.vao_decay.render(moderngl.TRIANGLES)

        # 2. emissive geometry -----------------------------------------
        ctx.enable(moderngl.BLEND)
        ctx.blend_func = (moderngl.ONE, moderngl.ONE)
        core = self.cfg.rgb["core"]
        if len(rib):
            self.vbo_ribbon.orphan(rib.nbytes)
            self.vbo_ribbon.write(rib.tobytes())
            self.prog_ribbon["u_res"] = (w, h)
            self.prog_ribbon["u_core"] = core
            self.prog_ribbon["u_time"] = t
            self.prog_ribbon["u_hum"] = float(post["mains_hum"])
            self.prog_ribbon["u_noise"] = float(post["tube_noise"])
            self.vao_ribbon.render(moderngl.TRIANGLES, vertices=len(rib))
        if len(dots):
            self.vbo_dot.orphan(dots.nbytes)
            self.vbo_dot.write(dots.tobytes())
            self.prog_dot["u_res"] = (w, h)
            self.prog_dot["u_core"] = core
            self.vao_dot.render(moderngl.TRIANGLES, vertices=6, instances=len(dots))

        self.trail_a, self.trail_b = self.trail_b, self.trail_a
        self.fb_trail_a, self.fb_trail_b = self.fb_trail_b, self.fb_trail_a

        # 3. bloom ------------------------------------------------------
        ctx.disable(moderngl.BLEND)
        self.bloom[0][1].use()
        self.trail_a.use(0)
        self.prog_thresh["u_tex"] = 0
        self.prog_thresh["u_thr"] = float(post["bloom_threshold"])
        self.prog_thresh["u_knee"] = float(post["bloom_knee"])
        self.vao_thresh.render(moderngl.TRIANGLES)
        for i in (1, 2):
            self.bloom[i][1].use()
            self.bloom[i - 1][0].use(0)
            self.prog_copy["u_tex"] = 0
            self.vao_copy.render(moderngl.TRIANGLES)
        for i in range(3):
            tex, fb = self.bloom[i]
            tmp, tmpfb = self.bloom_tmp[i]
            bw, bh = tex.size
            tmpfb.use()
            tex.use(0)
            self.prog_blur["u_tex"] = 0
            self.prog_blur["u_dir"] = (1.0 / bw, 0.0)
            self.vao_blur.render(moderngl.TRIANGLES)
            fb.use()
            tmp.use(0)
            self.prog_blur["u_dir"] = (0.0, 1.0 / bh)
            self.vao_blur.render(moderngl.TRIANGLES)

        # 4. tonemap to screen -----------------------------------------
        screen_fb.use()
        ctx.disable(moderngl.BLEND)
        self.trail_a.use(0)
        for i in range(3):
            self.bloom[i][0].use(1 + i)
        self.prog_tone["u_scene"] = 0
        self.prog_tone["u_b0"] = 1
        self.prog_tone["u_b1"] = 2
        self.prog_tone["u_b2"] = 3
        self.prog_tone["u_w"] = tuple(post["bloom_weights"])
        self.prog_tone["u_bg"] = self.cfg.rgb["background"]
        self.prog_tone["u_exposure"] = float(post["exposure"])
        self.prog_tone["u_gamma"] = float(post["gamma"])
        j = float(post["jitter_px"])
        self.prog_tone["u_jitter"] = (
            np.sin(t * 41.0) * j / w, np.cos(t * 37.0) * j / h)
        self.vao_tone.render(moderngl.TRIANGLES)

        # 5. solids on top ---------------------------------------------
        if len(solid):
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
            self.vbo_solid.orphan(solid.nbytes)
            self.vbo_solid.write(solid.tobytes())
            self.prog_solid["u_res"] = (w, h)
            self.vao_solid.render(moderngl.TRIANGLES, vertices=len(solid))
