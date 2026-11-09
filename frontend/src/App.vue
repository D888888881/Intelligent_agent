<template>
  <div class="wrap">
    <h1>Intelligent Agent — Vue 开发模式</h1>
    <p>
      当前前端运行在 Vite（端口见 <code>VITE_DEV_PORT</code>，默认 3000）。
      完整 ChatGPT 界面仍由 Django 模板提供。
    </p>
    <p>
      <a :href="djangoLogin" target="_blank" rel="noreferrer">打开 Django 主站（登录 / 聊天）</a>
    </p>
  </div>
</template>

<script setup>
const djangoPort = import.meta.env.VITE_DJANGO_PORT || "8088";
const djangoLogin = `http://127.0.0.1:${djangoPort}/login/`;
</script>

<style scoped>
.wrap {
  font-family: system-ui, sans-serif;
  max-width: 640px;
  margin: 48px auto;
  line-height: 1.6;
}
</style>
