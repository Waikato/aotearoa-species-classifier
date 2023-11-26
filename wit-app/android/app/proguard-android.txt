-keep class io.grpc.** {*;}
-keep class org.pytorch.** {*;}
-keep class com.facebook.** {*;}
-keepclassmembers enum * {
    public static **[] values();
    public static ** valueOf(java.lang.String);
}