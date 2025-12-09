我要用 python 写一个脚本：
全局变量： 
- inputDir 默认当前目录
- cookiesPath 默认 './cookies.txt'
- videoPath 默认 './todo'
- vibeModelPath 默认 "C:\Users\91658\AppData\Local\github.com.thewh1teagle.vibe\ggml-large-v3-turbo.bin"
- subtitlePath 默认 "./subtitle"
- promptPath 默认 './prompt'
- summaryPath 默认 './summary'
流程：
1.url 输入
读取要处理的视频url,url 可能从文件读取，文件来源于 inputDir
- input.txt（每一行一个 url）
- input.json（json 数组，元素是 url）,
2.url 处理
目前有两种形式
- https://www.bilibili.com/list/watchlater/?bvid=<vid>&... -> https://www.bilibili.com/video/<vid>
- https://www.bilibili.com/video/<vid> 直接使用
3.视频下载
根据获取到的 url，遍历执行 yt-dlp --cookies <cookiesPath> <url> 
- 上面的命令不全，需要追加参数，下载结果输出到 videoPath 下
- 可以并行执行
- 做抽象处理，支持替换视频下载工具
4.视频音频识别
遍历 videoPath 下的文件执行 vibe --model <vibeModelPath> --file <file_path> -l chinese --write <subtitlePath>/<file_name>.srt，然后将 srt 抹掉时间信息（去除多余的空行，每一段话一行即可）保存为 txt，然后删除 txt
- 执行命令前先检测 subtitlePath 已经存在同名的 txt，存在则不需要处理
- 可以并行执行
- 做抽象处理，支持替换音频识别工具
5.llm 总结
- 读取 <promptPath>/summary.md，遍历 txt，作为输入，逐个进行 llm api 总结调用，最终结果以 md 格式保存到 summaryPath 下
- llm 调用这里需要做抽象处理，到时可能会根据情况对接不同的 llm 实现
- 如果未提供 llm 实现，则跳过此过程

实现拆分不同模块，方便维护