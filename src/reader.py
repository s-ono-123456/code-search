CODE = """
package com.example.batch.processor;

import java.util.ArrayList;
import java.util.List;

import org.apache.ibatis.session.SqlSession;
import org.apache.ibatis.session.SqlSessionFactory;
import org.mybatis.spring.SqlSessionTemplate;
import org.springframework.batch.core.ChunkListener;
import org.springframework.batch.core.ExitStatus;
import org.springframework.batch.core.ItemWriteListener;
import org.springframework.batch.core.SkipListener;
import org.springframework.batch.core.StepExecution;
import org.springframework.batch.core.StepExecutionListener;
import org.springframework.batch.core.StepListener;
import org.springframework.batch.core.annotation.AfterWrite;
import org.springframework.batch.core.scope.context.ChunkContext;
import org.springframework.batch.item.Chunk;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.transaction.PlatformTransactionManager;

import com.example.batch.bean.ItemReaderBean01;
import com.example.batch.bean.ItemWriterBean01;
import com.example.batch.common.BaseProcessor;
import com.example.batch.mapper.SampleMapper;

@Component
public class ItemProcessor01 extends BaseProcessor<ItemReaderBean01, ItemWriterBean01>
		 implements SkipListener<ItemReaderBean01, ItemWriterBean01>
				   , StepListener, ChunkListener, StepExecutionListener, ItemWriteListener<ItemWriterBean01>{
    
	private int chunknum = 0;
	private int skipnum = 0;
	private List<Throwable> exceptions = new ArrayList<>();
    
	@Autowired
	private SqlSession sqlSession;
    
	@Autowired
	private SampleMapper sampleMapper;
    
	@Override
	protected ItemWriterBean01 executeIndividually(ItemReaderBean01 item) {
		ItemWriterBean01 output = new ItemWriterBean01();
		int id = Integer.parseInt(item.getId())+100;
		output.setTest(item.getTest() + "add");
		output.setData(item.getData());
		output.setId(Integer.toString(id));
		output.setDate(null);
        
		ItemWriterBean01 output2 = new ItemWriterBean01();
		int id2 = Integer.parseInt(item.getId())+200;
		output2.setTest(item.getTest() + "add");
		output2.setData(item.getData());
		output2.setId(Integer.toString(id2));
		output2.setDate(null);
        
		sampleMapper.insert001(output2);
        
		// これをつけると正常に更新できなくなる。
//        ItemWriterBean01 output3 = new ItemWriterBean01();
//        int id3 = Integer.parseInt(item.getId());
//        output3.setTest(item.getTest() + "add");
//        output3.setData(item.getData());
//        output3.setId(item.getId());
//
//        sampleMapper.update001(output3);
//        
		return output;
	}
    
	@Override
	public void onSkipInWrite(ItemWriterBean01 item, Throwable t) {
		// TODO 自動生成されたメソッド・スタブ
		SkipListener.super.onSkipInWrite(item, t);
		skipnum++;
		System.out.println("スキップ対象ID:" + item.getId());
		exceptions.add(t);
	}
    
	@Override
	public ExitStatus afterStep(StepExecution stepExecution) {
		// TODO 自動生成されたメソッド・スタブ
		System.out.println("スキップ件数：" + skipnum);
        
		return StepExecutionListener.super.afterStep(stepExecution);
	}
    
	@Override
	public void beforeChunk(ChunkContext context) {
		// TODO 自動生成されたメソッド・スタブ
		chunknum++;
		ChunkListener.super.beforeChunk(context);
		System.out.println(chunknum + "チャンク開始");
	}
	@Override
	public void afterWrite(Chunk<? extends ItemWriterBean01> items) {
		// TODO 自動生成されたメソッド・スタブ
		ItemWriteListener.super.afterWrite(items);
	}

}

"""