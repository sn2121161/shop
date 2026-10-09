"use client";

import { useEffect, useRef, useState } from "react";
import { Button, Spin, message } from "antd";
import { Bold, ImagePlus, Italic, Send, Underline } from "lucide-react";
import { api, apiErrorMessage, useShop } from "../shop";

type Comment = { id: number; author: string; content: string; createdAt: string };
type CommentImage = { id: number; url: string };

export default function ProductComments({ productId }: { productId: number }) {
  const { token, hydrate } = useShop();
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [imageIds, setImageIds] = useState<number[]>([]);
  const [notice, holder] = message.useMessage();
  const editorRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => { queueMicrotask(() => { void hydrate(); }); }, [hydrate]);
  useEffect(() => {
    let active = true;
    void api.get<Comment[]>(`/products/${productId}/comments`).then(({ data }) => {
      if (active) setComments(data);
    }).catch(() => {
      if (active) notice.error("评论暂时无法读取");
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [notice, productId]);

  const format = (command: "bold" | "italic" | "underline" | "foreColor", value?: string) => {
    editorRef.current?.focus();
    document.execCommand(command, false, value);
  };
  const uploadImage = async (file?: File) => {
    if (!file) return;
    if (!token) { notice.info("登录后即可上传评论图片"); return; }
    const form = new FormData();
    form.append("image", file);
    try {
      const { data } = await api.post<CommentImage>("/comment-images", form);
      editorRef.current?.focus();
      document.execCommand("insertImage", false, data.url);
      setImageIds((ids) => [...ids, data.id]);
    } catch (error: unknown) {
      notice.error(apiErrorMessage(error, "图片上传失败"));
    } finally {
      if (fileRef.current) fileRef.current.value = "";
    }
  };
  const submit = async () => {
    if (!token) { notice.info("登录后即可留言"); return; }
    const content = editorRef.current?.innerHTML.trim() || "";
    if (!content || content === "<br>") { notice.info("请输入评论内容"); return; }
    setSubmitting(true);
    try {
      const { data } = await api.post<Comment>(`/products/${productId}/comments`, { content, imageIds });
      setComments((current) => [data, ...current]);
      setImageIds([]);
      if (editorRef.current) editorRef.current.innerHTML = "";
      notice.success("评论已发布");
    } catch (error: unknown) {
      notice.error(apiErrorMessage(error, "评论发布失败"));
    } finally {
      setSubmitting(false);
    }
  };
  return <section className="product-comments" aria-labelledby="comments-title">{holder}<div className="comments-heading"><div><p className="eyebrow">COMMUNITY NOTES</p><h2 id="comments-title">留言</h2></div><span>{comments.length} 条评论</span></div><div className="comment-editor"><div className="comment-toolbar" role="toolbar" aria-label="富文本编辑工具"><Button type="text" icon={<Bold size={17} />} title="加粗" aria-label="加粗" onMouseDown={(event) => event.preventDefault()} onClick={() => format("bold")} /><Button type="text" icon={<Italic size={17} />} title="倾斜" aria-label="倾斜" onMouseDown={(event) => event.preventDefault()} onClick={() => format("italic")} /><Button type="text" icon={<Underline size={17} />} title="下划线" aria-label="下划线" onMouseDown={(event) => event.preventDefault()} onClick={() => format("underline")} /><label className="comment-color" title="文字颜色" aria-label="文字颜色"><input type="color" defaultValue="#265842" onChange={(event) => format("foreColor", event.target.value)} /></label><Button type="text" icon={<ImagePlus size={17} />} title="上传图片" aria-label="上传图片" onMouseDown={(event) => event.preventDefault()} onClick={() => fileRef.current?.click()} /></div><div ref={editorRef} className="comment-editor-content" contentEditable suppressContentEditableWarning data-placeholder="写下你对这件作品的感受" role="textbox" aria-multiline="true" /><input ref={fileRef} className="comment-file-input" type="file" accept="image/jpeg,image/png,image/webp,image/gif" onChange={(event) => { void uploadImage(event.target.files?.[0]); }} /><div className="comment-editor-footer"><span>支持文字颜色、加粗、倾斜、下划线和图片</span><Button type="primary" icon={<Send size={16} />} loading={submitting} onClick={submit}>发布评论</Button></div></div>{loading ? <div className="comments-loading"><Spin /></div> : <div className="comment-list">{comments.length ? comments.map((comment) => <article className="comment-item" key={comment.id}><header><strong>{comment.author}</strong><time dateTime={comment.createdAt}>{new Date(comment.createdAt).toLocaleDateString("zh-CN")}</time></header><div className="comment-content" dangerouslySetInnerHTML={{ __html: comment.content }} /></article>) : <p className="comments-empty">还没有留言，成为第一个分享感受的人。</p>}</div>}</section>;
}
