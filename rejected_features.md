1. Automatically restart if url expired: It's impossible to tell why the downloading fails from HTTP error code. keep restarts it could lead the program into dead loop

2. Overriding file extension with some flag - you can always rename the file after downloading if you really need it.

3. Downloading segments concurrently in python code: It can be useless for downloading is network-bound; A single TCP connection can consume all the bandwidth; Some CDNs have a per IP speed limitation. The implement can be messy. F.I. seg1 on CDN1, seg2 on CDN2, seg3 on CDN1 and CDN1 accepts only one connection per IP. If you really need this, try a third part backend.

---

1. 链接失效后自动重启解析：从HTTP的状态码看不出为什么下载失败，可能是链接失效，可能是别的原因。如果自动重新解析可能是在做无用功，一直重新解析可能死循环。

2. 提供一个覆盖扩展名的参数 - 如果真的要改扩展名，等下载结束后再改就可以了。

3. 在python代码里并发下载视频片段：在有些情况下可能没有用。例如一个TCP连接就耗掉了所有网速；例如有些CDN按IP限速。实现上也可能会比较混乱，例如片段1在CDN1上，片段2在CDN2，片段3又在CDN1，这时候如果CDN限制一个IP只能有一个链接，那么就需要一个专门的dispatcher才行。如果确实需要这个特性，建议用第三方工具（例如aria2）作为后端。 
