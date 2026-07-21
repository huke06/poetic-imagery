<template>
  <div class="max-w-xl mx-auto px-4 py-32 text-center">
    <p class="font-song text-8xl font-bold text-shiqing/20 select-none">迷 路</p>
    <h1 class="font-song text-2xl font-bold mt-6">寻寻觅觅，不见此页</h1>
    <p class="text-sm text-qianhui mt-3 leading-7">您访问的页面不存在或已被移动。<br />「欲穷千里目，更上一层楼」——不如回到首页重新出发。</p>
    <div class="flex items-center justify-center gap-4 mt-8">
      <router-link to="/" class="btn-primary">回到首页</router-link>
      <router-link to="/concepts" class="btn-outline">意象画廊</router-link>
    </div>
  </div>
</template>
